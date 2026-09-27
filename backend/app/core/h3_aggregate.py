"""Builds the per-request JSON "state" from the feature store: features,
area baselines, data gaps, and evidence IDs, area-weighted across the
parcel + 500m buffer's H3 cells.
"""

from __future__ import annotations

from collections import Counter

from app.core.parcels import Parcel
from app.datastore.bigquery_client import HazardFeatureStore

HAZARDS = ["flood", "subsidence", "wildfire", "heat", "landuse"]


def _aggregate_metric(rows: list[dict], key: str) -> float | str | None:
    """Numeric metrics (e.g. share_of_parcel_flooded) are area-weighted-
    averaged across cells; non-numeric metrics (e.g. landuse's
    change_type) take the most common value instead -- averaging a
    category label makes no sense."""
    values = [row["metrics"].get(key) for row in rows if not row["no_data"] and row["metrics"] and key in row["metrics"]]
    if not values:
        return None
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
        return sum(values) / len(values)
    return Counter(values).most_common(1)[0][0]


def aggregate_features(parcel: Parcel, store: HazardFeatureStore, per_hazard_versions: dict[str, str]) -> dict:
    all_cells = list(set(parcel.h3_cells) | set(parcel.buffer_cells))

    features: dict[str, dict] = {}
    data_gaps: list[str] = []
    evidence_ids: set[str] = set()

    for hazard in HAZARDS:
        version = per_hazard_versions.get(hazard)
        rows = store.get_hazard_features(all_cells, hazard, version)

        if not rows or all(row["no_data"] for row in rows):
            data_gaps.append(f"{hazard}: no usable observations for this parcel")
            features[hazard] = {}
            continue

        usable_rows = [row for row in rows if not row["no_data"]]
        metric_keys: set[str] = set()
        for row in usable_rows:
            if row.get("metrics"):
                metric_keys.update(row["metrics"].keys())

        aggregated = {key: _aggregate_metric(usable_rows, key) for key in metric_keys}
        features[hazard] = {k: v for k, v in aggregated.items() if v is not None}

        for row in usable_rows:
            evidence_ids.update(row.get("evidence_ids") or [])

        if len(usable_rows) < len(rows):
            data_gaps.append(f"{hazard}: some cells in this parcel's buffer had no usable observations")

    return {
        "parcel_id": parcel.parcel_id,
        "features": features,
        "data_gaps": data_gaps,
        "evidence_ids": sorted(evidence_ids),
    }
