"""Jev scoring client -- one call, all 12 questions, per the design doc's
requirement that Jev is "called once with all hazard questions."

Pin the model version (jev-1.13.0 by default via Settings.jev_model) --
never "jev-latest." Thresholds are re-tuned before any version bump, per
the design doc.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from typesafe_sdk import TypeSafeClient

from app.config import Settings
from app.scoring.jev_questions import QUESTIONS


@dataclass
class JevRawResult:
    answers: dict[str, Any]
    model: str

    @classmethod
    def from_sdk_response(cls, response: Any, model: str) -> "JevRawResult":
        # Verified against the installed typesafe_sdk (0.7.2):
        # SystemOneResponse has fields {model, usage, answers}, and answers
        # is keyed by question name -> ScoreAnswer/NoulAnswer/ChoiceAnswer
        # (fields: ScoreAnswer.score/.confidence/.legend/.probabilities,
        # NoulAnswer.noul, ChoiceAnswer.choice/.confidence/.probabilities).
        return cls(answers=dict(response.answers), model=response.model or model)


def score_with_jev(state: dict, settings: Settings) -> JevRawResult:
    with TypeSafeClient(api_key=settings.typesafe_api_key) as client:
        response = client.system_one(
            state=state,
            questions=QUESTIONS,
            model=settings.jev_model,
        )
    return JevRawResult.from_sdk_response(response, settings.jev_model)
