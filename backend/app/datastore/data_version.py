"""Per-hazard data_version stamping.

Each offline job stamps its own rows with a version string at write time,
independent of the other hazards' jobs -- this is what hazard_features is
keyed by. See version_registry.py for how these combine into the single
composite version used for the report cache key and the `reports` table.
"""

from datetime import date


def stamp_for_run(hazard: str, run_date: date) -> str:
    return f"{hazard}-{run_date:%Y%m%d}"
