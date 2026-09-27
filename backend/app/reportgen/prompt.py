"""Prompt construction for the LLM report writer.

Rules enforced by instruction (and checked by validator.py after the
fact): every factual sentence ends with an evidence ID like (E3); never
state a number absent from the evidence list; state risk levels exactly
as Jev/rule-baseline gave them, never softened or escalated.
"""

import json

from app.scoring.models import ScoringResult

SYSTEM_INSTRUCTIONS = """You are writing a parcel climate-risk report from pre-computed scores and cited evidence. Follow these rules exactly:

1. Every sentence that states a number or a hazard risk level must end with at least one evidence citation in the form (E1), (E2), etc., referencing the evidence list you are given.
2. Never state a number that does not appear, verbatim or rounded, in the evidence list you are given.
3. State each hazard's risk level exactly as given in the scores -- do not soften, escalate, or rephrase "high" as "moderate" or vice versa. If a level is "uncertain", say so plainly and mention why.
4. Write in plain language for a home buyer, but do not omit material findings.
5. Include a "Data gaps" section listing any hazards flagged as having no usable data.
6. Do not add a disclaimer -- one is appended automatically after your text.
"""


def build_prompt(scoring: ScoringResult, feature_state: dict, evidence: dict[str, dict]) -> str:
    scores_json = json.dumps(
        {hazard: score.model_dump() for hazard, score in scoring.hazards.items()}, indent=2
    )
    evidence_json = json.dumps(evidence, indent=2)
    data_gaps = feature_state.get("data_gaps", [])

    return f"""{SYSTEM_INSTRUCTIONS}

## Scores
{scores_json}

## Evidence (cite by key, e.g. (E1))
{evidence_json}

## Known data gaps
{json.dumps(data_gaps)}

## Land-use change type
{scoring.land_change_type}

## Needs expert review
{scoring.needs_expert_review}

Write the report now, in markdown, with one section per hazard (Flood, Subsidence, Wildfire, Heat, Land-use change) plus a short overall summary at the top and a "Data gaps" section."""


def build_regeneration_prompt(original_prompt: str, errors: list[str]) -> str:
    error_list = "\n".join(f"- {e}" for e in errors)
    return f"""{original_prompt}

Your previous draft failed validation for these specific reasons:
{error_list}

Regenerate the full report, fixing every issue above. Do not introduce new numbers or claims not in the evidence."""
