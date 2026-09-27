"""Shared scoring result shape so orchestrator code doesn't care whether a
hazard was scored by Jev or the rule-baseline fallback."""

from typing import Literal

from pydantic import BaseModel

Hazard = Literal["flood", "subsidence", "wildfire", "heat", "landuse"]
Level = Literal["low", "moderate", "high", "severe", "uncertain"]


class HazardScore(BaseModel):
    hazard: Hazard
    level: Level
    score_0_100: int
    confidence: float
    material_to_buyer: float
    source: Literal["jev", "rule_baseline"]
    conflict_note: str | None = None


class ScoringResult(BaseModel):
    hazards: dict[Hazard, HazardScore]
    land_change_type: Literal["new_development", "clearing", "wetland_loss", "none"]
    needs_expert_review: bool
    jev_version: str | None = None
