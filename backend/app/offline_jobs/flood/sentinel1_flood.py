"""Flood offline job: own Sentinel-1 threshold-based flood detection.

Design doc decision: build our own detection on known storm dates rather
than only relying on the Copernicus Global Flood Monitoring archive. For
each storm date, we compare a same-orbit Sentinel-1 VV scene against a
pre-storm baseline composite; pixels that drop sharply in VV backscatter
relative to baseline are flagged as flood water (radar-dark = smooth,
water-like surface). This is a simple, tunable heuristic, not a published
model -- validate against OpenFEMA claims / documented events before
trusting it (see design doc's evaluation plan).

Usage:
    python -m app.offline_jobs.flood.sentinel1_flood \
        --start-date 2015-01-01 --end-date 2026-01-01

Requires Earth Engine (see offline_jobs/common/ee_auth.py).
"""

from datetime import date, datetime, timezone

import ee

from app.config import get_settings
from app.datastore.bigquery_client import BigQueryFeatureStore
from app.datastore.data_version import stamp_for_run
from app.datastore.evidence_writer import write_evidence, write_hazard_features
from app.datastore.schema.row_models import EvidenceRow, HazardFeatureRow
from app.offline_jobs.common.ee_auth import init_earth_engine
from app.offline_jobs.common.job_base import JobRunSummary, build_arg_parser, configure_logging
from app.offline_jobs.flood.storm_dates import load_storm_dates

# VV backscatter drop (dB) below the pre-storm baseline that counts as flood
# water. Tune against OpenFEMA claims / documented events per the design
# doc's evaluation plan -- this starting value is not independently
# calibrated.
FLOOD_VV_DROP_THRESHOLD_DB = 6.0
BASELINE_WINDOW_DAYS = 30

METHOD_VERSION = "s1-vv-drop-v1"
SOURCE_PRODUCT = "COPERNICUS/S1_GRD"


def _austin_aoi() -> ee.Geometry:
    # Rough Travis County / Austin metro bounding box. Refine to the actual
    # pilot-metro boundary before running at scale.
    return ee.Geometry.Rectangle([-98.15, 30.05, -97.45, 30.65])


def _s1_collection(aoi: ee.Geometry, start: str, end: str) -> ee.ImageCollection:
    return (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(aoi)
        .filterDate(start, end)
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .select("VV")
    )


def _baseline_composite(aoi: ee.Geometry, storm_date: date) -> ee.Image:
    end = storm_date.isoformat()
    start = (storm_date.replace(day=1)).isoformat()
    coll = _s1_collection(aoi, start, end)
    return coll.median()


def detect_flood_extent(storm_image: ee.Image, baseline: ee.Image) -> ee.Image:
    """Binary flood mask: VV drop below baseline exceeds the threshold."""
    drop = baseline.subtract(storm_image)
    return drop.gt(FLOOD_VV_DROP_THRESHOLD_DB).rename("flood")


def run(start_date: date, end_date: date, h3_resolution: int, dry_run: bool) -> JobRunSummary:
    settings = get_settings()
    logger = configure_logging()
    init_earth_engine(settings)

    aoi = _austin_aoi()
    storm_dates = [d for d in load_storm_dates() if start_date <= d <= end_date]
    logger.info("Processing %d storm dates between %s and %s", len(storm_dates), start_date, end_date)

    summary = JobRunSummary(hazard="flood")
    store = BigQueryFeatureStore(settings) if not dry_run else None

    # NOTE: per-cell aggregation requires a concrete H3 grid over the AOI.
    # In production this should reuse the same cell set the `context` job
    # derives for the pilot metro (see offline_jobs/context/parcels_ingest.py)
    # rather than recomputing a full-metro polyfill here. Left as a TODO --
    # wire in the shared cell list once the context job has run.
    run_date = end_date
    data_version = stamp_for_run("flood", run_date)

    evidence_rows: list[EvidenceRow] = []
    feature_rows: list[HazardFeatureRow] = []

    for storm_date in storm_dates:
        storm_coll = _s1_collection(aoi, storm_date.isoformat(), (storm_date).isoformat())
        baseline = _baseline_composite(aoi, storm_date)
        storm_images = storm_coll.toList(storm_coll.size())

        if dry_run:
            logger.info("[dry-run] would process storm date %s", storm_date)
            continue

        evidence_id = f"E-flood-{storm_date:%Y%m%d}"
        evidence_rows.append(
            EvidenceRow(
                evidence_id=evidence_id,
                hazard="flood",
                source_product=SOURCE_PRODUCT,
                granule_ids=[],  # TODO: populate with actual scene IDs from storm_images
                date_start=storm_date,
                date_end=storm_date,
                method_version=METHOD_VERSION,
                values_json={"storm_date": storm_date.isoformat()},
                created_at=datetime.now(timezone.utc),
            )
        )

        # TODO: reduceRegions over the shared H3 cell FeatureCollection to get
        # per-cell flooded pixel share; this is the per-storm-date detection
        # call, deferred until the shared cell list (see NOTE above) exists.
        summary.evidence_rows_written += 1

    if not dry_run and evidence_rows:
        write_evidence(store, evidence_rows)
        if feature_rows:
            write_hazard_features(store, feature_rows)

    summary.log(logger)
    return summary


def main() -> None:
    parser = build_arg_parser("Flood offline job -- Sentinel-1 threshold detection")
    args = parser.parse_args()
    run(args.start_date, args.end_date, args.h3_resolution, args.dry_run)


if __name__ == "__main__":
    main()
