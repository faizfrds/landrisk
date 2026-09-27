"""Heat offline job: Landsat 8/9 land surface temperature summer composites.

Per design doc: cloud-masked June-August composite per year, cell mean
summer surface temp and difference from metro median. Surface temp, not
air temp -- one overpass time (~10:30am); this limitation is surfaced in
the report, not hidden.

Usage:
    python -m app.offline_jobs.heat.landsat_lst --start-date 2017-01-01 --end-date 2026-01-01
"""

from datetime import date, datetime, timezone

import ee

from app.config import get_settings
from app.datastore.bigquery_client import BigQueryFeatureStore
from app.datastore.evidence_writer import write_evidence
from app.datastore.schema.row_models import EvidenceRow
from app.offline_jobs.common.ee_auth import init_earth_engine
from app.offline_jobs.common.job_base import JobRunSummary, build_arg_parser, configure_logging

METHOD_VERSION = "landsat-c2-l2-summer-composite-v1"
SOURCE_PRODUCTS = ["LANDSAT/LC08/C02/T1_L2", "LANDSAT/LC09/C02/T1_L2"]

# USGS Collection 2 Level-2 ST_B10 scale/offset -> Kelvin, then to Celsius.
ST_SCALE = 0.00341802
ST_OFFSET = 149.0


def _austin_aoi() -> ee.Geometry:
    return ee.Geometry.Rectangle([-98.15, 30.05, -97.45, 30.65])


def _cloud_mask(image: ee.Image) -> ee.Image:
    qa = image.select("QA_PIXEL")
    cloud_bit = 1 << 3
    cloud_shadow_bit = 1 << 4
    mask = qa.bitwiseAnd(cloud_bit).eq(0).And(qa.bitwiseAnd(cloud_shadow_bit).eq(0))
    return image.updateMask(mask)


def _lst_celsius(image: ee.Image) -> ee.Image:
    kelvin = image.select("ST_B10").multiply(ST_SCALE).add(ST_OFFSET)
    return kelvin.subtract(273.15).rename("lst_c")


def summer_composite(year: int, aoi: ee.Geometry) -> ee.Image:
    start, end = f"{year}-06-01", f"{year}-09-01"
    images = []
    for product in SOURCE_PRODUCTS:
        coll = ee.ImageCollection(product).filterBounds(aoi).filterDate(start, end).map(_cloud_mask).map(_lst_celsius)
        images.append(coll)
    merged = images[0].merge(images[1])
    return merged.median().clip(aoi)


def run(start_date: date, end_date: date, h3_resolution: int, dry_run: bool) -> JobRunSummary:
    settings = get_settings()
    logger = configure_logging()
    summary = JobRunSummary(hazard="heat")

    if dry_run:
        logger.info("[dry-run] would build summer LST composites for %s..%s", start_date, end_date)
        summary.log(logger)
        return summary

    init_earth_engine(settings)
    aoi = _austin_aoi()
    store = BigQueryFeatureStore(settings)

    years = range(start_date.year, end_date.year + 1)
    evidence_rows = []
    for year in years:
        composite = summer_composite(year, aoi)
        # TODO: reduceRegions over the shared H3 cell FeatureCollection for
        # per-cell mean LST, plus a full-AOI reducer for the metro median;
        # write hazard_features rows with metrics={"mean_lst_c": ..., "delta_vs_metro_median_c": ...}.
        evidence_rows.append(
            EvidenceRow(
                evidence_id=f"E-heat-{year}",
                hazard="heat",
                source_product="+".join(SOURCE_PRODUCTS),
                granule_ids=[],
                date_start=date(year, 6, 1),
                date_end=date(year, 8, 31),
                method_version=METHOD_VERSION,
                values_json={"year": year},
                created_at=datetime.now(timezone.utc),
            )
        )

    write_evidence(store, evidence_rows)
    summary.evidence_rows_written = len(evidence_rows)
    summary.log(logger)
    return summary


def main() -> None:
    parser = build_arg_parser("Heat offline job -- Landsat surface temperature composites")
    args = parser.parse_args()
    run(args.start_date, args.end_date, args.h3_resolution, args.dry_run)


if __name__ == "__main__":
    main()
