"""Subsidence offline job: NASA OPERA DISP-S1 surface displacement.

OPEN ITEM (flagged in the plan): OPERA DISP-S1 is distributed via NASA
Earthdata / ASF DAAC, not Earth Engine's public catalog -- this job uses
`earthaccess`, unlike the flood/heat/landuse jobs which use `ee`. Requires
EARTHDATA_TOKEN (new credential, see .env.example).

OPEN ITEM: DISP-S1 coverage is North-America-wide per NASA's product
description, but Travis County / Austin specifically has not been
independently confirmed here -- verify before relying on this job's output
(this is the design doc's own called-out risk for this hazard).

Usage:
    python -m app.offline_jobs.subsidence.opera_subsidence \
        --start-date 2016-01-01 --end-date 2026-01-01
"""

from datetime import date, datetime, timezone

import earthaccess
import numpy as np
import rasterio
import rioxarray  # noqa: F401 -- registers the .rio accessor used below

from app.config import get_settings
from app.datastore.bigquery_client import BigQueryFeatureStore
from app.datastore.evidence_writer import write_evidence
from app.datastore.schema.row_models import EvidenceRow
from app.offline_jobs.common.job_base import JobRunSummary, build_arg_parser, configure_logging

METHOD_VERSION = "opera-disp-s1-linear-fit-v1"
SOURCE_PRODUCT = "OPERA_L3_DISP-S1"

# Rough Travis County / Austin metro bounding box, (west, south, east, north).
AUSTIN_BBOX = (-98.15, 30.05, -97.45, 30.65)


def _login() -> None:
    settings = get_settings()
    if not settings.earthdata_token:
        raise RuntimeError(
            "EARTHDATA_TOKEN is not set. Register free at "
            "https://urs.earthdata.nasa.gov/ and add it to .env."
        )
    earthaccess.login(strategy="environment")


def search_granules(start_date: date, end_date: date) -> list:
    return earthaccess.search_data(
        short_name="OPERA_L3_DISP-S1",
        bounding_box=AUSTIN_BBOX,
        temporal=(start_date.isoformat(), end_date.isoformat()),
    )


def fit_velocity(epoch_dates: list[date], displacements_mm: list[float]) -> tuple[float, float]:
    """Linear velocity (mm/yr) and residual std (fit error) for one cell."""
    t0 = epoch_dates[0]
    years = np.array([(d - t0).days / 365.25 for d in epoch_dates])
    values = np.array(displacements_mm)
    slope, intercept = np.polyfit(years, values, 1)
    residuals = values - (slope * years + intercept)
    fit_error = float(np.std(residuals))
    return float(slope), fit_error


def sample_at_centroids(granule_paths: list[str], h3_cell_centroids: dict[str, tuple[float, float]]) -> dict:
    """Sample displacement rasters at each H3 cell centroid.

    Returns {h3_cell: [(epoch_date, displacement_mm), ...]}. TODO: wire in
    the actual per-granule epoch date parsing from OPERA filenames/metadata
    once real granules are downloaded -- left as a structural stub since we
    cannot execute earthaccess downloads without live credentials here.
    """
    results: dict[str, list[tuple[date, float]]] = {cell: [] for cell in h3_cell_centroids}
    for path in granule_paths:
        with rasterio.open(path) as src:
            for cell, (lat, lon) in h3_cell_centroids.items():
                row, col = src.index(lon, lat)
                value = src.read(1)[row, col]
                # TODO: parse the real epoch date from granule metadata.
                results[cell].append((date.today(), float(value)))
    return results


def run(start_date: date, end_date: date, h3_resolution: int, dry_run: bool) -> JobRunSummary:
    logger = configure_logging()
    settings = get_settings()
    summary = JobRunSummary(hazard="subsidence")

    if dry_run:
        logger.info("[dry-run] would search OPERA DISP-S1 granules for %s..%s", start_date, end_date)
        summary.log(logger)
        return summary

    _login()
    granules = search_granules(start_date, end_date)
    logger.info("Found %d OPERA DISP-S1 granules", len(granules))
    if not granules:
        summary.warnings.append(
            "No OPERA DISP-S1 granules found for the Austin AOI -- coverage may not "
            "include Travis County. Cells should be written with no_data=True."
        )
        summary.log(logger)
        return summary

    # TODO: download granules (earthaccess.download), sample at the shared
    # H3 cell centroid set (see flood job's NOTE re: shared cell list), fit
    # velocity per cell, and write hazard_features/evidence rows. Structural
    # stub only -- requires live credentials + downloaded granules to
    # complete end-to-end.
    store = BigQueryFeatureStore(settings)
    run_date = end_date
    evidence_rows: list[EvidenceRow] = [
        EvidenceRow(
            evidence_id=f"E-subsidence-{run_date:%Y%m%d}",
            hazard="subsidence",
            source_product=SOURCE_PRODUCT,
            granule_ids=[g.get("meta", {}).get("concept-id", "") for g in granules[:5]],
            date_start=start_date,
            date_end=end_date,
            method_version=METHOD_VERSION,
            values_json={"granule_count": len(granules)},
            created_at=datetime.now(timezone.utc),
        )
    ]
    write_evidence(store, evidence_rows)

    summary.log(logger)
    return summary


def main() -> None:
    parser = build_arg_parser("Subsidence offline job -- NASA OPERA DISP-S1")
    args = parser.parse_args()
    run(args.start_date, args.end_date, args.h3_resolution, args.dry_run)


if __name__ == "__main__":
    main()
