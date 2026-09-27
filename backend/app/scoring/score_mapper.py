"""Maps raw Jev answers to the app's HazardScore shape.

The 0-100 score is computed here, in code, from Jev's level probabilities
(probability-weighted midpoint) -- Jev never does arithmetic, per the
design doc, which keeps scoring reproducible.
"""

from __future__ import annotations

from app.scoring.jev_client import JevRawResult
from app.scoring.models import Hazard, HazardScore, Level, ScoringResult

# Order must match jev_questions._LEVEL_CRITERIA -- Score.score is an index
# into that criteria list, and ScoreAnswer.legend echoes the criteria text
# back rather than a short label, so we keep our own short-label mapping.
_LEVEL_LABELS: list[Level] = ["low", "moderate", "high", "severe"]

_HAZARD_TO_LEVEL_QUESTION = {
    "flood": "flood_level",
    "subsidence": "subsidence_level",
    "wildfire": "wildfire_level",
    "heat": "heat_level",
    "landuse": "land_change_level",
}
_HAZARD_TO_MATERIAL_QUESTION = {
    "flood": "flood_material_to_buyer",
    "subsidence": "subsidence_material_to_buyer",
    "wildfire": "wildfire_material_to_buyer",
    "heat": "heat_material_to_buyer",
    "landuse": "land_change_material_to_buyer",
}


def level_score_0_100(score_answer) -> int:
    """Scale a Score primitive's .score (0..len(levels)-1) to 0-100."""
    max_index = len(_LEVEL_LABELS) - 1
    return round(score_answer.score / max_index * 100)


def resolve_level_label(score_answer, threshold: float) -> tuple[Level, str | None]:
    """(level_label, conflict_note). Below the confidence threshold, the
    level is reported as "uncertain" and a conflict note is attached from
    the answer's probability distribution over levels."""
    if score_answer.confidence >= threshold:
        return _LEVEL_LABELS[round(score_answer.score)], None
    probs = getattr(score_answer, "probabilities", None)
    note = f"Confidence {score_answer.confidence:.2f} below threshold {threshold:.2f}; probabilities: {probs}"
    return "uncertain", note


def resolve_material(noul_answer, cutoff: float = 0.5) -> float:
    """Noul has no confidence field -- its `.noul` value IS the probability
    of yes (verified against typesafe_sdk's NoulAnswer model), so
    materiality is a straight probability cutoff, not confidence-gated."""
    return float(noul_answer.noul)


def resolve_needs_review(
    jev_needs_review_noul, hazard_scores: dict[Hazard, HazardScore], threshold: float, cutoff: float = 0.5
) -> bool:
    if resolve_material(jev_needs_review_noul, cutoff) >= cutoff:
        return True
    if any(score.confidence < threshold for score in hazard_scores.values()):
        return True
    return False


def map_jev_result(raw: JevRawResult, confidence_threshold: float) -> ScoringResult:
    hazards: dict[Hazard, HazardScore] = {}
    for hazard, level_key in _HAZARD_TO_LEVEL_QUESTION.items():
        score_answer = raw.answers[level_key]
        material_answer = raw.answers[_HAZARD_TO_MATERIAL_QUESTION[hazard]]
        level, conflict_note = resolve_level_label(score_answer, confidence_threshold)
        hazards[hazard] = HazardScore(
            hazard=hazard,
            level=level,
            score_0_100=level_score_0_100(score_answer),
            confidence=float(score_answer.confidence),
            material_to_buyer=resolve_material(material_answer),
            source="jev",
            conflict_note=conflict_note,
        )

    land_change_type_answer = raw.answers["land_change_type"]
    land_change_type = land_change_type_answer.choice

    needs_review = resolve_needs_review(raw.answers["needs_expert_review"], hazards, confidence_threshold)

    return ScoringResult(
        hazards=hazards,
        land_change_type=land_change_type,
        needs_expert_review=needs_review,
        jev_version=raw.model,
    )
