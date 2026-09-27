"""Wildfire offline job (part 1): NASA FIRMS VIIRS active fire archive.

Requires FIRMS_MAP_KEY (new credential, see .env.example -- register free
at https://firms.modaps.eosdis.nasa.gov/api/map_key/).

Per design doc: fire counts within 1/5/10 km of each H3 cell since 2012.
"""

from datetime import date, datetime, timedelta, timezone
from math import atan2, cos, radians, sin, sqrt

import httpx

from app.config import get_settings
from app.datastore.bigquery_client import BigQueryFeatureStore
from app.datastore.evidence_writer import write_evidence
from app.datastore.schema.row_models import EvidenceRow
from app.offline_jobs.common.job_base import JobRunSummary, build_arg_parser, configure_logging

METHOD_VERSION = "firms-viirs-ring-count-v1"
SOURCE_PRODUCT = "NASA_FIRMS_VIIRS_SNPP_NRT"
RING_DISTANCES_KM = (1, 5, 10)
AUSTIN_BBOX = "-98.15,30.05,-97.45,30.65"  # west,south,east,north


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * r * atan2(sqrt(a), sqrt(1 - a))


def fetch_firms_archive(map_key: str, start_date: date, end_date: date) -> list[dict]:
    """Pull VIIRS fire detections for the AOI, paging in <=10-day windows
    (FIRMS archive API caps the day range per request)."""
    detections: list[dict] = []
    day_range = 10
    cursor = start_date
    with httpx.Client(timeout=30.0) as client:
        while cursor <= end_date:
            span = min(day_range, (end_date - cursor).days + 1)
            url = (
                f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}/"
                f"VIIRS_SNPP_SP/{AUSTIN_BBOX}/{span}/{cursor.isoformat()}"
            )
            resp = client.get(url)
            resp.raise_for_status()
            lines = resp.text.strip().splitlines()
            if len(lines) > 1:
                header = lines[0].split(",")
                for line in lines[1:]:
                    values = line.split(",")
                    detections.append(dict(zip(header, values)))
            cursor = cursor + timedelta(days=span)
    return detections


def fire_counts_within_rings(
    cell_centroid: tuple[float, float], detections: list[dict]
) -> dict[int, int]:
    lat, lon = cell_centroid
    counts = {km: 0 for km in RING_DISTANCES_KM}
    for det in detections:
        try:
            d_lat, d_lon = float(det["latitude"]), float(det["longitude"])
        except (KeyError, ValueError):
            continue
        dist = _haversine_km(lat, lon, d_lat, d_lon)
        for km in RING_DISTANCES_KM:
            if dist <= km:
                counts[km] += 1
    return counts


def run(start_date: date, end_date: date, h3_resolution: int, dry_run: bool) -> JobRunSummary:
    logger = configure_logging()
    settings = get_settings()
    summary = JobRunSummary(hazard="wildfire")

    if not settings.firms_map_key:
        summary.warnings.append(
            "FIRMS_MAP_KEY is not set. Register free at "
            "https://firms.modaps.eosdis.nasa.gov/api/map_key/ and add it to .env."
        )
        if not dry_run:
            summary.log(logger)
            return summary

    if dry_run:
        logger.info("[dry-run] would fetch FIRMS VIIRS archive for %s..%s", start_date, end_date)
        summary.log(logger)
        return summary

    detections = fetch_firms_archive(settings.firms_map_key, start_date, end_date)
    logger.info("Fetched %d VIIRS detections", len(detections))

    # TODO: iterate the shared H3 cell centroid set for the pilot metro
    # (see flood job's NOTE re: shared cell list from the context job) and
    # call fire_counts_within_rings per cell, then write hazard_features
    # rows. Structural stub -- the ring-count function above is complete
    # and unit-testable on its own.
    store = BigQueryFeatureStore(settings)
    run_date = end_date
    evidence_rows = [
        EvidenceRow(
            evidence_id=f"E-wildfire-{run_date:%Y%m%d}",
            hazard="wildfire",
            source_product=SOURCE_PRODUCT,
            granule_ids=[],
            date_start=start_date,
            date_end=end_date,
            method_version=METHOD_VERSION,
            values_json={"detection_count": len(detections)},
            created_at=datetime.now(timezone.utc),
        )
    ]
    write_evidence(store, evidence_rows)

    summary.log(logger)
    return summary


def main() -> None:
    parser = build_arg_parser("Wildfire offline job -- NASA FIRMS VIIRS archive")
    args = parser.parse_args()
    run(args.start_date, args.end_date, args.h3_resolution, args.dry_run)


if __name__ == "__main__":
    main()
