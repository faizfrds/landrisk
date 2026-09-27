"""End-to-end smoke test of the online path, fully hermetic: fake BigQuery,
fake Redis, monkeypatched geocoding/Jev/LLM. Exercises geocode -> parcel
resolution -> cache check -> H3 aggregation -> scoring -> report writing ->
PDF render -> cache write, including the data-gaps path (the fixture's
subsidence rows are all no_data=True).
"""

from dataclasses import dataclass

import pytest

from app.api.schemas import ReportResponse
from app.core import orchestrator
from app.core.geocode import GeocodeResult
from app.scoring.models import HazardScore, ScoringResult


@dataclass
class _FakePdfBytes:
    pass


@pytest.fixture(autouse=True)
def _patch_external_calls(monkeypatch, seeded_parcel):
    async def fake_geocode(address: str) -> GeocodeResult:
        return GeocodeResult(lat=seeded_parcel["lat"], lon=seeded_parcel["lon"], matched_address=address)

    monkeypatch.setattr(orchestrator, "geocode_address", fake_geocode)

    def fake_score(feature_state: dict, settings) -> ScoringResult:
        hazards = {
            hazard: HazardScore(
                hazard=hazard,
                level="low",
                score_0_100=10,
                confidence=0.9,
                material_to_buyer=0.2,
                source="rule_baseline",
            )
            for hazard in ["flood", "subsidence", "wildfire", "heat", "landuse"]
        }
        return ScoringResult(hazards=hazards, land_change_type="none", needs_expert_review=False)

    monkeypatch.setattr(orchestrator, "_score", fake_score)

    def fake_write_report(scoring, feature_state, evidence, settings) -> str:
        lines = ["# Parcel Risk Report", "", "## Flood", "Observed risk level: low (E1)."]
        if feature_state.get("data_gaps"):
            lines += ["", "## Data gaps"] + [f"- {g}" for g in feature_state["data_gaps"]]
        return "\n".join(lines)

    monkeypatch.setattr(orchestrator, "write_report", fake_write_report)

    def fake_render_pdf(report_md, report_id, parcel_id, data_version) -> bytes:
        return b"%PDF-1.4 fake"

    monkeypatch.setattr(orchestrator, "render_pdf", fake_render_pdf)


@pytest.mark.asyncio
async def test_generate_report_end_to_end(fake_store, fake_redis, seeded_parcel):
    events = []
    final_response = None

    async for item in orchestrator.generate_report(
        "301 Congress Ave, Austin, TX", fake_store, fake_redis
    ):
        if isinstance(item, ReportResponse):
            final_response = item
        else:
            events.append(item)

    assert final_response is not None
    assert final_response.parcel_id == seeded_parcel["parcel_id"]
    assert "subsidence: no usable observations for this parcel" in final_response.data_gaps
    assert final_response.report_md.startswith("# Parcel Risk Report")

    stages = [e.stage for e in events]
    assert stages[0] == "geocoding"
    assert "done" in stages

    cached = fake_redis.get(f"report:{final_response.parcel_id}:{final_response.data_version}")
    assert cached is not None

    pdf_bytes = orchestrator.get_pdf_bytes(final_response.report_id)
    assert pdf_bytes == b"%PDF-1.4 fake"


@pytest.mark.asyncio
async def test_generate_report_cache_hit(fake_store, fake_redis, seeded_parcel):
    first_events = []
    async for item in orchestrator.generate_report("301 Congress Ave, Austin, TX", fake_store, fake_redis):
        first_events.append(item)
    first_response = next(e for e in first_events if isinstance(e, ReportResponse))

    second_stages = []
    final_response = None
    async for item in orchestrator.generate_report("301 Congress Ave, Austin, TX", fake_store, fake_redis):
        if isinstance(item, ReportResponse):
            final_response = item
        else:
            second_stages.append(item.stage)

    assert final_response.report_id == first_response.report_id
    assert "checking_cache" in second_stages
    assert "aggregating_features" not in second_stages
