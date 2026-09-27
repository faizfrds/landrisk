"""Shared write path for all 6 offline jobs.

Two invariants the design doc requires, enforced here rather than trusted
to each job:
  - `no_data` is always explicit -- a cell with no usable observation must
    never be silently written as a zero/low-risk value.
  - Every AlphaEarth-derived evidence row carries its CC-BY-4.0 license
    (AlphaEarth is the one source in this project that requires
    attribution; see the design doc's licensing risk).
Both writers raise on partial-insert errors -- offline jobs should fail
loudly, not silently drop rows.
"""

from __future__ import annotations

from app.datastore.bigquery_client import HazardFeatureStore
from app.datastore.schema.row_models import EvidenceRow, HazardFeatureRow


def write_hazard_features(store: HazardFeatureStore, rows: list[HazardFeatureRow]) -> None:
    for row in rows:
        if not row.no_data and not row.evidence_ids:
            raise ValueError(
                f"hazard_features row for {row.h3_cell}/{row.hazard} has no evidence_ids "
                "but no_data is False -- every scored cell must cite evidence."
            )
    payload = [row.model_dump(mode="json") for row in rows]
    store.insert_hazard_features(payload)


def write_evidence(store: HazardFeatureStore, records: list[EvidenceRow]) -> None:
    for record in records:
        # landuse evidence is exclusively AlphaEarth-derived in this project
        # (see offline_jobs/landuse/alphaearth_embeddings.py) -- AlphaEarth
        # is CC-BY 4.0 and requires attribution.
        if record.hazard == "landuse" and record.license != "CC-BY-4.0":
            raise ValueError(
                f"AlphaEarth-derived evidence {record.evidence_id} must set license='CC-BY-4.0'"
            )
    payload = [record.model_dump(mode="json") for record in records]
    store.insert_evidence(payload)
