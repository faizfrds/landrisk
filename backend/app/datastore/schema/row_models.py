"""Pydantic mirrors of the BigQuery row shapes in ddl.sql.

These validate rows before insert; they are the Python-side contract, not a
duplicate of the DDL -- the DDL is still the schema source of truth.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

Hazard = Literal["flood", "subsidence", "wildfire", "heat", "landuse"]


class HazardFeatureRow(BaseModel):
    h3_cell: str
    hazard: Hazard
    data_version: str
    metrics: dict | None = None
    no_data: bool
    evidence_ids: list[str] = []
    computed_at: datetime


class EvidenceRow(BaseModel):
    evidence_id: str
    hazard: Hazard | None = None
    source_product: str
    granule_ids: list[str] = []
    date_start: date | None = None
    date_end: date | None = None
    method_version: str
    values_json: dict | None = None
    license: str | None = None
    created_at: datetime


class ParcelRow(BaseModel):
    parcel_id: str
    county_fips: str | None = None
    address: str | None = None
    geometry_wkt: str
    h3_cells: list[str] = []
    buffer_cells: list[str] = []
    source: Literal["travis_county_parcel", "point_buffer_fallback"]
    created_at: datetime


class ReportRow(BaseModel):
    report_id: str
    parcel_id: str
    data_version: str
    jev_version: str | None = None
    llm_model: str | None = None
    scores: dict
    report_md: str
    needs_expert_review: bool
    data_gaps: list[str] = []
    center_lat: float
    center_lon: float
    created_at: datetime
