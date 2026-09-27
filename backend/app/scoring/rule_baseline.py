"""Deterministic rule-baseline scorer.

Per design doc: this is (a) the automatic fallback when Jev is unavailable,
and (b) the benchmark Jev must beat before shipping as the default (see
app/eval/README.md). Thresholds below are starting points, not tuned --
tune against the design doc's per-hazard ground-truth checks once a
labeled set exists.

Confidence here is fixed and lower than a well-calibrated Jev response,
by design: a hand-written threshold rule cannot express genuine
uncertainty the way a calibrated model can, so we deliberately signal it's
a lower-fidelity fallback via a flat 0.5 confidence.
"""

from __future__ import annotations

from app.scoring.models import Hazard, HazardScore, Level, ScoringResult

RULE_BASELINE_CONFIDENCE = 0.5

_LEVEL_LABELS: list[Level] = ["low", "moderate", "high", "severe"]


def _bucket(value: float, thresholds: tuple[float, float, float]) -> Level:
    low_high, high_high, severe_high = thresholds
    if value < low_high:
        return "low"
    if value < high_high:
        return "moderate"
    if value < severe_high:
        return "high"
    return "severe"


def _score_0_100(level: Level) -> int:
    index = _LEVEL_LABELS.index(level)
    return round(index / (len(_LEVEL_LABELS) - 1) * 100)


def score_flood(metrics: dict) -> HazardScore:
    share_flooded = metrics.get("share_of_parcel_flooded", 0.0)
    level = _bucket(share_flooded, (0.05, 0.2, 0.5))
    return HazardScore(
        hazard="flood", level=level, score_0_100=_score_0_100(level),
        confidence=RULE_BASELINE_CONFIDENCE, material_to_buyer=1.0 if level != "low" else 0.3,
        source="rule_baseline",
    )


def score_subsidence(metrics: dict) -> HazardScore:
    velocity_mm_yr = abs(metrics.get("velocity_mm_per_year", 0.0))
    level = _bucket(velocity_mm_yr, (2.0, 5.0, 10.0))
    return HazardScore(
        hazard="subsidence", level=level, score_0_100=_score_0_100(level),
        confidence=RULE_BASELINE_CONFIDENCE, material_to_buyer=1.0 if level != "low" else 0.3,
        source="rule_baseline",
    )


def score_wildfire(metrics: dict) -> HazardScore:
    fires_within_5km = metrics.get("fire_count_5km", 0)
    distance_to_burn_km = metrics.get("distance_to_nearest_burn_km", float("inf"))
    if distance_to_burn_km < 1 or fires_within_5km > 10:
        level: Level = "severe"
    elif distance_to_burn_km < 5 or fires_within_5km > 3:
        level = "high"
    elif fires_within_5km > 0:
        level = "moderate"
    else:
        level = "low"
    return HazardScore(
        hazard="wildfire", level=level, score_0_100=_score_0_100(level),
        confidence=RULE_BASELINE_CONFIDENCE, material_to_buyer=1.0 if level != "low" else 0.3,
        source="rule_baseline",
    )


def score_heat(metrics: dict) -> HazardScore:
    delta_c = metrics.get("delta_vs_metro_median_c", 0.0)
    level = _bucket(delta_c, (1.0, 2.5, 4.0))
    return HazardScore(
        hazard="heat", level=level, score_0_100=_score_0_100(level),
        confidence=RULE_BASELINE_CONFIDENCE, material_to_buyer=1.0 if level != "low" else 0.3,
        source="rule_baseline",
    )


def score_landuse(metrics: dict) -> HazardScore:
    share_changed = metrics.get("share_buffer_changed", 0.0)
    level = _bucket(share_changed, (0.05, 0.15, 0.35))
    return HazardScore(
        hazard="landuse", level=level, score_0_100=_score_0_100(level),
        confidence=RULE_BASELINE_CONFIDENCE, material_to_buyer=1.0 if level != "low" else 0.3,
        source="rule_baseline",
    )


_SCORERS = {
    "flood": score_flood,
    "subsidence": score_subsidence,
    "wildfire": score_wildfire,
    "heat": score_heat,
    "landuse": score_landuse,
}


def score_with_rule_baseline(feature_state: dict) -> ScoringResult:
    hazards: dict[Hazard, HazardScore] = {}
    for hazard, scorer in _SCORERS.items():
        metrics = feature_state.get("features", {}).get(hazard, {})
        hazards[hazard] = scorer(metrics)

    landuse_metrics = feature_state.get("features", {}).get("landuse", {})
    land_change_type = landuse_metrics.get("change_type", "none")

    needs_review = any(h.level == "severe" for h in hazards.values())

    return ScoringResult(
        hazards=hazards,
        land_change_type=land_change_type,
        needs_expert_review=needs_review,
        jev_version=None,
    )
