"""Loads the same fixture JSON used by the hermetic pytest smoke test into
the REAL BigQuery dev dataset, so the manual end-to-end smoke test
(scripts/smoke_test.py) can exercise the online path against real
BigQuery/Redis without ever running a real offline batch job first.

Run `python -m app.datastore.schema.create_tables` first.

Usage:
    python -m scripts.seed_bigquery
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.datastore.bigquery_client import BigQueryFeatureStore

FIXTURES_DIR = Path(__file__).parents[1] / "tests" / "fixtures"


def _load(name: str) -> list[dict]:
    return json.loads((FIXTURES_DIR / name).read_text())


def main() -> None:
    settings = get_settings()
    store = BigQueryFeatureStore(settings)

    now = datetime.now(timezone.utc).isoformat()

    parcels = _load("seed_parcels.json")
    for parcel in parcels:
        row = {k: v for k, v in parcel.items() if k not in ("lat", "lon")}
        row["created_at"] = now
        store.insert_parcel(row)
    print(f"Seeded {len(parcels)} parcel(s)")

    evidence = _load("seed_evidence.json")
    for row in evidence:
        row["created_at"] = now
    store.insert_evidence(evidence)
    print(f"Seeded {len(evidence)} evidence row(s)")

    hazard_features = _load("seed_hazard_features.json")
    for row in hazard_features:
        row["computed_at"] = now
    store.insert_hazard_features(hazard_features)
    print(f"Seeded {len(hazard_features)} hazard_features row(s)")

    print(
        "Seeding complete. The seeded parcel is at "
        f"lat={parcels[0]['lat']}, lon={parcels[0]['lon']} -- use an address that "
        "geocodes near there (see scripts/smoke_test.py) for the manual smoke test."
    )


if __name__ == "__main__":
    main()
