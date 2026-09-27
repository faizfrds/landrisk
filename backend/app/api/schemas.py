"""Response models mirroring the design doc's abridged report JSON shape,
plus one additive field (`cells`) needed for the frontend's toggleable
Google Maps hazard layers -- not in the original doc, non-breaking.
"""

from typing import Literal

from pydantic import BaseModel

from app.scoring.models import Hazard, Level


class EvidenceItem(BaseModel):
    source: str
    dates: str
    value: str


class HazardResult(BaseModel):
    level: Level
    score: int
    confidence: float
    material_to_buyer: float
    evidence: list[str]


class CellScore(BaseModel):
    h3_cell: str
    hazard: Hazard
    score_0_100: int


class Coordinates(BaseModel):
    lat: float
    lon: float


class ReportResponse(BaseModel):
    report_id: str
    parcel_id: str
    data_version: str
    hazards: dict[Hazard, HazardResult]
    needs_expert_review: bool
    data_gaps: list[str]
    evidence: dict[str, EvidenceItem]
    report_md: str
    cells: list[CellScore] = []
    center: Coordinates


class ProgressEvent(BaseModel):
    stage: Literal[
        "geocoding", "resolving_parcel", "checking_cache", "aggregating_features",
        "scoring", "writing_report", "rendering_pdf", "done", "error",
    ]
    message: str


class ReportRequest(BaseModel):
    address: str
