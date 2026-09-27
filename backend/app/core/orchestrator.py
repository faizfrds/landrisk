"""The online request path, as an async generator yielding ProgressEvents
and finishing with a ReportResponse, per the design doc's 7-step flow:

1. Geocode the address, resolve the parcel (fallback to point buffer).
2. Check the report cache; return on hit.
3. Aggregate hazard features across the parcel + 500m buffer's H3 cells.
4. Build the JSON state (features, baselines, data gaps, evidence IDs).
5. Score with Jev (rule-baseline as automatic fallback on error/timeout).
6. Write the report (LLM + validator + regenerate/template fallback).
7. Render the PDF, cache, write the durable row, return.

Both the blocking and SSE-streaming API handlers drive this same
generator -- the blocking handler just drains it to the final value.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator

import redis

from app.api.schemas import CellScore, Coordinates, EvidenceItem, HazardResult, ProgressEvent, ReportResponse
from app.config import Settings, get_settings
from app.core.cache import get_cached_report, set_cached_report
from app.core.geocode import geocode_address
from app.core.h3_aggregate import HAZARDS, aggregate_features
from app.core.parcels import resolve_parcel
from app.datastore.bigquery_client import HazardFeatureStore
from app.datastore.version_registry import current_composite_version
from app.pdf.render import render_pdf
from app.reportgen.pipeline import write_report
from app.scoring.jev_client import score_with_jev
from app.scoring.models import ScoringResult
from app.scoring.rule_baseline import score_with_rule_baseline
from app.scoring.score_mapper import map_jev_result

logger = logging.getLogger("core.orchestrator")


def _score(feature_state: dict, settings: Settings) -> ScoringResult:
    try:
        raw = score_with_jev(feature_state, settings)
        return map_jev_result(raw, settings.jev_confidence_threshold)
    except Exception:  # noqa: BLE001 -- any Jev failure/timeout falls back
        logger.exception("Jev scoring failed; falling back to rule baseline")
        return score_with_rule_baseline(feature_state)


def _build_evidence_lookup(store: HazardFeatureStore, evidence_ids: list[str]) -> dict[str, dict]:
    rows = store.get_evidence_by_ids(evidence_ids)
    return {row["evidence_id"]: row for row in rows}


async def generate_report(
    address: str,
    store: HazardFeatureStore,
    redis_client: redis.Redis,
) -> AsyncIterator[ProgressEvent | ReportResponse]:
    settings = get_settings()
    stage_start = time.monotonic()

    def _elapsed() -> float:
        return time.monotonic() - stage_start

    yield ProgressEvent(stage="geocoding", message=f"Looking up {address}…")
    geocode_result = await geocode_address(address)
    logger.info("geocode: %.2fs", _elapsed())

    yield ProgressEvent(stage="resolving_parcel", message="Finding the parcel boundary…")
    parcel = resolve_parcel(geocode_result, store)
    logger.info("resolve_parcel: %.2fs", _elapsed())

    per_hazard_versions = {h: store.get_max_data_version(h) or "none" for h in HAZARDS}
    data_version = current_composite_version(store, redis_client)

    yield ProgressEvent(stage="checking_cache", message="Checking for a cached report…")
    cached = get_cached_report(redis_client, parcel.parcel_id, data_version)
    if cached is not None:
        yield ReportResponse(**cached)
        return

    yield ProgressEvent(stage="aggregating_features", message="Checking flood, heat, and fire history…")
    feature_state = aggregate_features(parcel, store, per_hazard_versions)
    logger.info("aggregate_features: %.2fs", _elapsed())

    yield ProgressEvent(stage="scoring", message="Scoring each hazard…")
    scoring = _score(feature_state, settings)
    logger.info("scoring: %.2fs", _elapsed())

    evidence_lookup = _build_evidence_lookup(store, feature_state["evidence_ids"])

    yield ProgressEvent(stage="writing_report", message="Writing your report…")
    report_md = write_report(scoring, feature_state, evidence_lookup, settings)
    logger.info("write_report: %.2fs", _elapsed())

    report_id = f"rpt_{uuid.uuid4().hex[:20]}"

    hazards_out = {
        hazard: HazardResult(
            level=score.level,
            score=score.score_0_100,
            confidence=score.confidence,
            material_to_buyer=score.material_to_buyer,
            evidence=[eid for eid in evidence_lookup if evidence_lookup[eid].get("hazard") == hazard],
        )
        for hazard, score in scoring.hazards.items()
    }
    evidence_out = {
        eid: EvidenceItem(
            source=row.get("source_product", ""),
            dates=f"{row.get('date_start', '')}..{row.get('date_end', '')}",
            value=str(row.get("values_json", "")),
        )
        for eid, row in evidence_lookup.items()
    }
    cells_out = [
        CellScore(h3_cell=cell, hazard=hazard, score_0_100=scoring.hazards[hazard].score_0_100)
        for hazard in HAZARDS
        for cell in parcel.h3_cells
    ]

    response = ReportResponse(
        report_id=report_id,
        parcel_id=parcel.parcel_id,
        data_version=data_version,
        hazards=hazards_out,
        needs_expert_review=scoring.needs_expert_review,
        data_gaps=feature_state["data_gaps"],
        evidence=evidence_out,
        report_md=report_md,
        cells=cells_out,
        center=Coordinates(lat=geocode_result.lat, lon=geocode_result.lon),
    )

    yield ProgressEvent(stage="rendering_pdf", message="Rendering the PDF…")
    pdf_bytes = render_pdf(report_md, report_id, parcel.parcel_id, data_version)

    set_cached_report(redis_client, parcel.parcel_id, data_version, response.model_dump(mode="json"))
    store.insert_report(
        {
            "report_id": report_id,
            "parcel_id": parcel.parcel_id,
            "data_version": data_version,
            "jev_version": scoring.jev_version,
            "llm_model": settings.gemini_model,
            "scores": {h: s.model_dump() for h, s in scoring.hazards.items()},
            "report_md": report_md,
            "needs_expert_review": scoring.needs_expert_review,
            "data_gaps": feature_state["data_gaps"],
            "center_lat": geocode_result.lat,
            "center_lon": geocode_result.lon,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    _store_pdf_bytes(report_id, pdf_bytes)

    yield ProgressEvent(stage="done", message="Report ready.")
    yield response


# In-memory PDF cache for this pass -- the durable copy is report_md in
# BigQuery; PDFs are cheap to re-render from it on demand. A real deploy
# would persist rendered PDFs to object storage instead of memory.
_pdf_cache: dict[str, bytes] = {}


def _store_pdf_bytes(report_id: str, pdf_bytes: bytes) -> None:
    _pdf_cache[report_id] = pdf_bytes


def get_pdf_bytes(report_id: str) -> bytes | None:
    return _pdf_cache.get(report_id)
