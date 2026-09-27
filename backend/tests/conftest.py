"""Hermetic test fixtures: FakeBigQueryClient (in-memory) and fakeredis.
test_orchestrator_smoke.py additionally monkeypatches geocoding, Jev, and
the LLM client so the whole test is zero-credential, zero-network.
"""

import json
from pathlib import Path

import fakeredis
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> list[dict]:
    return json.loads((FIXTURES_DIR / name).read_text())


class FakeBigQueryClient:
    """In-memory double for the narrow HazardFeatureStore interface."""

    def __init__(self):
        self.hazard_features = _load_fixture("seed_hazard_features.json")
        self.evidence = _load_fixture("seed_evidence.json")
        self.parcels = _load_fixture("seed_parcels.json")
        self.reports: dict[str, dict] = {}

    def get_hazard_features(self, h3_cells, hazard, data_version=None):
        return [
            row
            for row in self.hazard_features
            if row["hazard"] == hazard
            and row["h3_cell"] in h3_cells
            and (data_version is None or row["data_version"] == data_version)
        ]

    def get_parcel(self, parcel_id):
        return next((p for p in self.parcels if p["parcel_id"] == parcel_id), None)

    def find_parcel_containing(self, lat, lon):
        for p in self.parcels:
            if abs(p["lat"] - lat) < 0.01 and abs(p["lon"] - lon) < 0.01:
                return p
        return None

    def get_max_data_version(self, hazard):
        versions = [row["data_version"] for row in self.hazard_features if row["hazard"] == hazard]
        return max(versions) if versions else None

    def insert_hazard_features(self, rows):
        self.hazard_features.extend(rows)

    def insert_evidence(self, rows):
        self.evidence.extend(rows)

    def insert_parcel(self, row):
        self.parcels.append(row)

    def insert_report(self, row):
        self.reports[row["report_id"]] = row

    def get_report(self, report_id):
        return self.reports.get(report_id)

    def get_evidence_by_ids(self, evidence_ids):
        return [row for row in self.evidence if row["evidence_id"] in evidence_ids]


@pytest.fixture
def fake_store():
    return FakeBigQueryClient()


@pytest.fixture
def fake_redis():
    return fakeredis.FakeRedis()


@pytest.fixture
def seeded_parcel(fake_store):
    return fake_store.parcels[0]
