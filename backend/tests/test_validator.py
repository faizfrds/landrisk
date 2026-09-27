from app.reportgen.validator import validate
from app.scoring.models import HazardScore, ScoringResult

EVIDENCE = {
    "E1": {"hazard": "flood", "values_json": {"flooded_events": 3, "total_events": 11}},
}


def _scoring():
    hazards = {
        "flood": HazardScore(hazard="flood", level="high", score_0_100=70, confidence=0.9, material_to_buyer=0.9, source="jev"),
        "subsidence": HazardScore(hazard="subsidence", level="low", score_0_100=5, confidence=0.9, material_to_buyer=0.1, source="jev"),
        "wildfire": HazardScore(hazard="wildfire", level="low", score_0_100=5, confidence=0.9, material_to_buyer=0.1, source="jev"),
        "heat": HazardScore(hazard="heat", level="low", score_0_100=5, confidence=0.9, material_to_buyer=0.1, source="jev"),
        "landuse": HazardScore(hazard="landuse", level="low", score_0_100=5, confidence=0.9, material_to_buyer=0.1, source="jev"),
    }
    return ScoringResult(hazards=hazards, land_change_type="none", needs_expert_review=False)


def test_validate_passes_with_correct_citation():
    report_md = "## Flood\nThis parcel flooded in 3 of 11 recorded events (E1), a high risk level."
    result = validate(report_md, EVIDENCE, _scoring())
    assert result.passed, result.errors


def test_validate_fails_on_uncited_number():
    report_md = "## Flood\nThis parcel flooded in 3 of 11 recorded events, a high risk level."
    result = validate(report_md, EVIDENCE, _scoring())
    assert not result.passed
    assert any("no evidence citation" in e for e in result.errors)


def test_validate_fails_on_fabricated_number():
    report_md = "## Flood\nThis parcel flooded in 99 of 11 recorded events (E1), a high risk level."
    result = validate(report_md, EVIDENCE, _scoring())
    assert not result.passed
    assert any("not found in evidence" in e for e in result.errors)


def test_validate_fails_on_nonexistent_evidence_id():
    report_md = "## Flood\nThis parcel flooded in 3 of 11 recorded events (E99), a high risk level."
    result = validate(report_md, EVIDENCE, _scoring())
    assert not result.passed
    assert any("does not exist" in e for e in result.errors)


def test_validate_fails_on_level_mismatch():
    report_md = "## Flood\nThis parcel's flood risk is low (E1), based on 3 of 11 events."
    result = validate(report_md, EVIDENCE, _scoring())
    assert not result.passed
    assert any("flood" in e for e in result.errors)
