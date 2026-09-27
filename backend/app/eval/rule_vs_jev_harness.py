"""Stub for the Phase 3 gate: "Jev beats the rule baseline before it ships
as the default scorer." See README.md in this directory for what this
needs once a labeled parcel set exists -- deliberately not implemented in
this pass (prototype scope, no 300-parcel labeling effort yet).
"""

from dataclasses import dataclass


@dataclass
class LabeledParcel:
    parcel_id: str
    hand_labeled_levels: dict[str, str]  # hazard -> low|moderate|high|severe


@dataclass
class ComparisonReport:
    jev_accuracy: float
    rule_baseline_accuracy: float
    jev_calibration_error: float
    reports_routed_to_review: int


def compare(labeled_parcels: list[LabeledParcel]) -> ComparisonReport:
    raise NotImplementedError(
        "Requires a hand-labeled parcel set -- see app/eval/README.md. "
        "Not built in this pass (prototype scope)."
    )
