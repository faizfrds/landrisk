"""Report generation pipeline: draft -> validate -> regenerate once on
failure -> templated fallback on second failure. Every path appends the
fixed disclaimer.
"""

from __future__ import annotations

import logging

from app.config import Settings
from app.reportgen.disclaimer import DISCLAIMER
from app.reportgen.fallback_template import build_templated_report
from app.reportgen.llm_client import generate_report_md
from app.reportgen.prompt import build_prompt, build_regeneration_prompt
from app.reportgen.validator import validate
from app.scoring.models import ScoringResult

logger = logging.getLogger("reportgen.pipeline")


def write_report(
    scoring: ScoringResult,
    feature_state: dict,
    evidence: dict[str, dict],
    settings: Settings,
) -> str:
    data_gaps = feature_state.get("data_gaps", [])
    prompt = build_prompt(scoring, feature_state, evidence)

    draft = _try_generate(prompt, settings)
    result = validate(draft, evidence, scoring) if draft is not None else None

    if draft is not None and not result.passed:
        logger.warning("Report draft failed validation: %s", result.errors)
        regen_prompt = build_regeneration_prompt(prompt, result.errors)
        draft = _try_generate(regen_prompt, settings)
        result = validate(draft, evidence, scoring) if draft is not None else None

    if draft is None or not result.passed:
        if draft is not None:
            logger.warning("Regenerated draft still failed validation: %s -- using templated fallback", result.errors)
        draft = build_templated_report(scoring, evidence, data_gaps)

    return f"{draft}\n\n---\n\n{DISCLAIMER}"


def _try_generate(prompt: str, settings: Settings) -> str | None:
    """The LLM call can fail outright (network, auth, an invalid model id)
    -- not just fail validation. Per the design doc's principle that the AI
    layer never hard-fails the pipeline (Jev already falls back to the rule
    baseline the same way), any such failure here also falls through to the
    templated report rather than raising a 500."""
    try:
        return generate_report_md(prompt, settings)
    except Exception:  # noqa: BLE001
        logger.exception("LLM report generation call failed")
        return None
