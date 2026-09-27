"""Fixed set of 12 typed Jev questions, per the design doc's "decompose
multi-factor judgments, all answered in one parallel call" guidance.

OPEN ITEM / DEVIATION FROM THE DESIGN DOC'S PROSE (flagged during planning,
confirmed with the user): the doc's prose says "Choice" for the 5 ordered
hazard-level questions. TypeSafe's own docs describe `Score` as the
primitive for an ordered dimension, returning a probability-weighted
midpoint natively -- exactly what the design doc wants computed "in code."
We use `Score` for the 5 level questions and reserve `Choice` for
`land_change_type`, which is genuinely unordered.

Re-verify the typesafe_sdk import surface against https://docs.typesafe.ai
before relying on this -- Jev is early access and the API may have moved
since this was checked during planning.
"""

from typesafe_sdk import Choice, Noul, Score

_LEVEL_CRITERIA = [
    "low: no material observed signal above the area baseline",
    "moderate: some observed signal, within a range a typical buyer would want disclosed but not alarming",
    "high: a clear, repeated, or recent observed signal materially above the area baseline",
    "severe: an extreme or repeated observed signal, or a very recent severe event",
]

_HAZARD_LABELS = {
    "flood": "flood risk, based on the observed satellite flood history and area baseline",
    "subsidence": "ground subsidence risk, based on observed vertical velocity and trend vs. area average",
    "wildfire": "wildfire risk, based on nearby fire history and distance to past burns",
    "heat": "extreme heat risk, based on observed summer surface temperature vs. the metro median",
    "land_change": "risk from nearby land-use change, based on the observed change share and type",
}


def _level_question(hazard_key: str) -> Score:
    return Score(
        instructions=f"How severe is this parcel's {_HAZARD_LABELS[hazard_key]}?",
        criteria=_LEVEL_CRITERIA,
    )


def _materiality_question(hazard_key: str) -> Noul:
    return Noul(
        instructions=(
            f"Would a typical home buyer want to know about this parcel's "
            f"{_HAZARD_LABELS[hazard_key]} before purchase?"
        )
    )


QUESTIONS = {
    "flood_level": _level_question("flood"),
    "subsidence_level": _level_question("subsidence"),
    "wildfire_level": _level_question("wildfire"),
    "heat_level": _level_question("heat"),
    "land_change_level": _level_question("land_change"),
    "flood_material_to_buyer": _materiality_question("flood"),
    "subsidence_material_to_buyer": _materiality_question("subsidence"),
    "wildfire_material_to_buyer": _materiality_question("wildfire"),
    "heat_material_to_buyer": _materiality_question("heat"),
    "land_change_material_to_buyer": _materiality_question("land_change"),
    "land_change_type": Choice(
        instructions="What type of nearby land-use change, if any, was detected in the buffer around this parcel?",
        criteria={
            "new_development": "construction of new buildings or impervious surface",
            "clearing": "vegetation or tree cover removed without new construction",
            "wetland_loss": "loss of wetland or surface water area",
            "none": "no material land-use change detected",
        },
    ),
    "needs_expert_review": Noul(
        instructions=(
            "Do the hazard signals in this state conflict with each other, or does any "
            "signal fall outside normal observed ranges, such that this report should be "
            "queued for expert review before being shown as-is?"
        )
    ),
}
