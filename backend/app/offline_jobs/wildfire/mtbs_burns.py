"""Wildfire offline job (part 2): MTBS burn perimeters.

MTBS (Monitoring Trends in Burn Severity) perimeter shapefiles are not
behind an API key -- download manually from https://www.mtbs.gov/direct-
download and place under backend/data/reference/mtbs/ before running this
job. Per design doc: distance to nearest past burn perimeter, per H3 cell.
"""

import argparse
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point

from app.config import get_settings
from app.datastore.bigquery_client import BigQueryFeatureStore
from app.datastore.evidence_writer import write_evidence
from app.datastore.schema.row_models import EvidenceRow
from app.offline_jobs.common.job_base import JobRunSummary, configure_logging

METHOD_VERSION = "mtbs-nearest-perimeter-v1"
SOURCE_PRODUCT = "MTBS_burn_perimeters"
MTBS_DIR = Path(__file__).parents[3] / "data" / "reference" / "mtbs"


def load_perimeters() -> gpd.GeoDataFrame:
    shapefiles = list(MTBS_DIR.glob("*.shp"))
    if not shapefiles:
        raise FileNotFoundError(
            f"No MTBS shapefiles found in {MTBS_DIR}. Download from "
            "https://www.mtbs.gov/direct-download and place them there."
        )
    frames = [gpd.read_file(path) for path in shapefiles]
    return gpd.GeoDataFrame(pd_concat(frames))


def pd_concat(frames):  # thin wrapper to avoid importing pandas at module load time
    import pandas as pd

    return pd.concat(frames, ignore_index=True)


def nearest_burn_distance_m(point: Point, perimeters: gpd.GeoDataFrame) -> float:
    distances = perimeters.geometry.distance(point)
    return float(distances.min()) if len(distances) else float("inf")


def run(h3_resolution: int, dry_run: bool) -> JobRunSummary:
    logger = configure_logging()
    settings = get_settings()
    summary = JobRunSummary(hazard="wildfire")

    if dry_run:
        logger.info("[dry-run] would load MTBS perimeters from %s", MTBS_DIR)
        summary.log(logger)
        return summary

    try:
        perimeters = load_perimeters()
    except FileNotFoundError as exc:
        summary.warnings.append(str(exc))
        summary.log(logger)
        return summary

    logger.info("Loaded %d MTBS burn perimeters", len(perimeters))

    # TODO: iterate the shared H3 cell centroid set for the pilot metro and
    # call nearest_burn_distance_m per cell, then write hazard_features
    # rows alongside the FIRMS ring counts from firms_viirs.py (both feed
    # the same "wildfire" hazard).
    store = BigQueryFeatureStore(settings)
    evidence_rows = [
        EvidenceRow(
            evidence_id="E-wildfire-mtbs",
            hazard="wildfire",
            source_product=SOURCE_PRODUCT,
            granule_ids=[],
            method_version=METHOD_VERSION,
            values_json={"perimeter_count": len(perimeters)},
            created_at=datetime.now(timezone.utc),
        )
    ]
    write_evidence(store, evidence_rows)

    summary.log(logger)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Wildfire offline job -- MTBS burn perimeters")
    parser.add_argument("--h3-resolution", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(args.h3_resolution, args.dry_run)


if __name__ == "__main__":
    main()
