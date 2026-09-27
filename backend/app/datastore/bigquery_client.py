"""Thin BigQuery access layer for the feature store.

Every method here has a narrow, testable signature so `tests/conftest.py`
can substitute a `FakeBigQueryClient` implementing the same interface,
without touching real BigQuery in the hermetic smoke test.
"""

from __future__ import annotations

from typing import Protocol

from google.cloud import bigquery

from app.config import Settings


class HazardFeatureStore(Protocol):
    def get_hazard_features(
        self, h3_cells: list[str], hazard: str, data_version: str | None = None
    ) -> list[dict]: ...

    def get_parcel(self, parcel_id: str) -> dict | None: ...

    def find_parcel_containing(self, lat: float, lon: float) -> dict | None: ...

    def get_max_data_version(self, hazard: str) -> str | None: ...

    def insert_hazard_features(self, rows: list[dict]) -> None: ...

    def insert_evidence(self, rows: list[dict]) -> None: ...

    def insert_parcel(self, row: dict) -> None: ...

    def insert_report(self, row: dict) -> None: ...

    def get_report(self, report_id: str) -> dict | None: ...

    def get_evidence_by_ids(self, evidence_ids: list[str]) -> list[dict]: ...


class BigQueryFeatureStore:
    """Real implementation, backed by google-cloud-bigquery."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = bigquery.Client(project=settings.gcp_project_id)
        self.dataset = f"{settings.gcp_project_id}.{settings.bq_dataset}"

    def get_hazard_features(
        self, h3_cells: list[str], hazard: str, data_version: str | None = None
    ) -> list[dict]:
        version_clause = "AND data_version = @data_version" if data_version else ""
        query = f"""
            SELECT h3_cell, hazard, data_version, metrics, no_data, evidence_ids, computed_at
            FROM `{self.dataset}.hazard_features`
            WHERE hazard = @hazard AND h3_cell IN UNNEST(@h3_cells)
            {version_clause}
        """
        params = [
            bigquery.ScalarQueryParameter("hazard", "STRING", hazard),
            bigquery.ArrayQueryParameter("h3_cells", "STRING", h3_cells),
        ]
        if data_version:
            params.append(bigquery.ScalarQueryParameter("data_version", "STRING", data_version))
        job = self.client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=params))
        return [dict(row) for row in job.result()]

    def get_parcel(self, parcel_id: str) -> dict | None:
        query = f"SELECT * FROM `{self.dataset}.parcels` WHERE parcel_id = @parcel_id LIMIT 1"
        params = [bigquery.ScalarQueryParameter("parcel_id", "STRING", parcel_id)]
        job = self.client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=params))
        rows = list(job.result())
        return dict(rows[0]) if rows else None

    def find_parcel_containing(self, lat: float, lon: float) -> dict | None:
        query = f"""
            SELECT * FROM `{self.dataset}.parcels`
            WHERE ST_CONTAINS(geometry, ST_GEOGPOINT(@lon, @lat))
            LIMIT 1
        """
        params = [
            bigquery.ScalarQueryParameter("lat", "FLOAT64", lat),
            bigquery.ScalarQueryParameter("lon", "FLOAT64", lon),
        ]
        job = self.client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=params))
        rows = list(job.result())
        return dict(rows[0]) if rows else None

    def get_max_data_version(self, hazard: str) -> str | None:
        query = f"""
            SELECT MAX(data_version) AS max_version
            FROM `{self.dataset}.hazard_features`
            WHERE hazard = @hazard
        """
        params = [bigquery.ScalarQueryParameter("hazard", "STRING", hazard)]
        job = self.client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=params))
        rows = list(job.result())
        return rows[0]["max_version"] if rows else None

    def insert_hazard_features(self, rows: list[dict]) -> None:
        errors = self.client.insert_rows_json(f"{self.dataset}.hazard_features", rows)
        if errors:
            raise RuntimeError(f"hazard_features insert errors: {errors}")

    def insert_evidence(self, rows: list[dict]) -> None:
        errors = self.client.insert_rows_json(f"{self.dataset}.evidence", rows)
        if errors:
            raise RuntimeError(f"evidence insert errors: {errors}")

    def insert_parcel(self, row: dict) -> None:
        errors = self.client.insert_rows_json(f"{self.dataset}.parcels", [row])
        if errors:
            raise RuntimeError(f"parcels insert errors: {errors}")

    def insert_report(self, row: dict) -> None:
        errors = self.client.insert_rows_json(f"{self.dataset}.reports", [row])
        if errors:
            raise RuntimeError(f"reports insert errors: {errors}")

    def get_report(self, report_id: str) -> dict | None:
        query = f"SELECT * FROM `{self.dataset}.reports` WHERE report_id = @report_id LIMIT 1"
        params = [bigquery.ScalarQueryParameter("report_id", "STRING", report_id)]
        job = self.client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=params))
        rows = list(job.result())
        return dict(rows[0]) if rows else None

    def get_evidence_by_ids(self, evidence_ids: list[str]) -> list[dict]:
        query = f"SELECT * FROM `{self.dataset}.evidence` WHERE evidence_id IN UNNEST(@ids)"
        params = [bigquery.ArrayQueryParameter("ids", "STRING", evidence_ids)]
        job = self.client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=params))
        return [dict(row) for row in job.result()]
