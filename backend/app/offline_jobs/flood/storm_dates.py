"""Curated list of known Austin-area flood/storm dates since 2015.

STARTER PLACEHOLDER: the dates in storm_dates_austin.csv were assembled from
general knowledge of major Central Texas flood events, not verified against
a primary source. Research and replace before relying on this for real
scoring -- see design doc's flood job description ("known storm dates").
"""

import csv
from datetime import date
from pathlib import Path

CSV_PATH = Path(__file__).parents[3] / "data" / "reference" / "storm_dates_austin.csv"


def load_storm_dates() -> list[date]:
    with CSV_PATH.open() as f:
        reader = csv.DictReader(f)
        return [date.fromisoformat(row["date"]) for row in reader]
