"""Deterministic, non-LLM report built directly from scores + evidence.

Used when the LLM draft fails validation twice in a row -- passes
validation by construction (every claim is generated with its own
citation, values are pulled directly from the evidence records). The
pipeline never ships an unvalidated report.
"""

from app.scoring.models import ScoringResult

_HAZARD_TITLES = {
    "flood": "Flood",
    "subsidence": "Ground subsidence",
    "wildfire": "Wildfire",
    "heat": "Extreme heat",
    "landuse": "Land-use change",
}


def build_templated_report(scoring: ScoringResult, evidence: dict[str, dict], data_gaps: list[str]) -> str:
    lines = ["# Parcel Risk Report", "", "## Summary", ""]
    for hazard, score in scoring.hazards.items():
        lines.append(
            f"- **{_HAZARD_TITLES[hazard]}**: {score.level} (score {score.score_0_100}/100, "
            f"confidence {score.confidence:.2f})"
        )
    lines += ["", "## Detail", ""]

    for hazard, score in scoring.hazards.items():
        lines.append(f"### {_HAZARD_TITLES[hazard]}")
        evidence_ids = [eid for eid in evidence if evidence[eid].get("hazard") == hazard]
        citation = f"({', '.join(evidence_ids)})" if evidence_ids else ""
        note = f" {score.conflict_note}" if score.conflict_note else ""
        lines.append(f"Observed risk level: **{score.level}** {citation}.{note}")
        lines.append("")

    lines += ["## Land-use change type", f"{scoring.land_change_type}", ""]

    if data_gaps:
        lines += ["## Data gaps", ""]
        for gap in data_gaps:
            lines.append(f"- {gap}")
        lines.append("")

    if scoring.needs_expert_review:
        lines.append("_This report has been flagged for expert review due to conflicting or out-of-range signals._")

    return "\n".join(lines)
