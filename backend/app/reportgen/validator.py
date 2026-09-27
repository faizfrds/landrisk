"""Validates an LLM-drafted report before it ships.

Three checks per the design doc:
  1. Every sentence with a number or hazard claim cites >=1 evidence ID.
  2. Every cited ID exists, and every number in that sentence matches a
     value in that evidence record.
  3. The stated risk levels match the scoring layer's output.

This is the guard against "LLM invents or distorts a claim" (design doc's
top-listed AI risk after false reassurance from missing data). On failure
the caller (pipeline.py) regenerates once, then falls back to a templated
report that is correct by construction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.scoring.models import ScoringResult

_EVIDENCE_ID_PATTERN = re.compile(r"\(E(\d+)\)")
_NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")
_HAZARD_KEYWORDS = ("flood", "subsidence", "wildfire", "heat", "land-use", "land use")
_LEVEL_WORDS = ("low", "moderate", "high", "severe", "uncertain")


@dataclass
class ValidationResult:
    passed: bool
    errors: list[str] = field(default_factory=list)


def _split_sentences(report_md: str) -> list[str]:
    # Skip markdown headers; split remaining text on sentence boundaries.
    lines = [line for line in report_md.splitlines() if not line.strip().startswith("#")]
    text = " ".join(lines)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _flatten_evidence_values(evidence_record: dict) -> list[str]:
    values = evidence_record.get("values_json") or evidence_record.get("value") or {}
    flat: list[str] = []

    def _walk(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, (list, tuple)):
            for v in obj:
                _walk(v)
        else:
            flat.append(str(obj))

    _walk(values)
    return flat


def _check_citations_present(sentences: list[str]) -> list[str]:
    errors = []
    for sentence in sentences:
        has_number = bool(_NUMBER_PATTERN.search(sentence))
        has_hazard_keyword = any(kw in sentence.lower() for kw in _HAZARD_KEYWORDS)
        if (has_number or has_hazard_keyword) and not _EVIDENCE_ID_PATTERN.search(sentence):
            errors.append(f"Sentence makes a claim with no evidence citation: \"{sentence[:120]}\"")
    return errors


def _check_citation_correctness(sentences: list[str], evidence: dict[str, dict]) -> list[str]:
    errors = []
    for sentence in sentences:
        cited_ids = [f"E{m}" for m in _EVIDENCE_ID_PATTERN.findall(sentence)]
        if not cited_ids:
            continue
        numbers_in_sentence = _NUMBER_PATTERN.findall(sentence)
        for eid in cited_ids:
            if eid not in evidence:
                errors.append(f"Cited evidence id {eid} does not exist: \"{sentence[:120]}\"")
                continue
            if numbers_in_sentence:
                allowed_values = _flatten_evidence_values(evidence[eid])
                for number in numbers_in_sentence:
                    if not any(number in allowed for allowed in allowed_values):
                        errors.append(
                            f"Number '{number}' in sentence not found in evidence {eid}: \"{sentence[:120]}\""
                        )
    return errors


def _check_level_consistency(report_md: str, scoring: ScoringResult) -> list[str]:
    errors = []
    lower = report_md.lower()
    for hazard, score in scoring.hazards.items():
        hazard_heading_pos = lower.find(hazard.replace("_", " "))
        if hazard_heading_pos == -1:
            continue
        window = lower[hazard_heading_pos : hazard_heading_pos + 500]
        stated_levels = [w for w in _LEVEL_WORDS if w in window]
        if score.level not in stated_levels and stated_levels:
            errors.append(
                f"{hazard}: scoring says level='{score.level}' but report section mentions {stated_levels} instead"
            )
    return errors


def validate(report_md: str, evidence: dict[str, dict], scoring: ScoringResult) -> ValidationResult:
    sentences = _split_sentences(report_md)
    errors: list[str] = []
    errors += _check_citations_present(sentences)
    errors += _check_citation_correctness(sentences, evidence)
    errors += _check_level_consistency(report_md, scoring)
    return ValidationResult(passed=not errors, errors=errors)
