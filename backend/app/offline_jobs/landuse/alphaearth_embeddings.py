"""Land-use change offline job (part 1): AlphaEarth annual embeddings.

OPEN ITEM: the exact Earth Engine catalog asset ID for AlphaEarth is not
independently verified -- `GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL` is a
placeholder. Confirm the real asset path in the Earth Engine Data Catalog
before running.

AlphaEarth is CC-BY 4.0 -- every evidence row derived from it must carry
license="CC-BY-4.0" (enforced in evidence_writer.write_evidence).

Per design doc: cosine similarity between consecutive years per 10m pixel,
flag pixels below a tuned threshold, aggregate to "share of buffer changed"
per H3 cell.
"""

from datetime import date, datetime, timezone

import ee

from app.config import get_settings
from app.datastore.bigquery_client import BigQueryFeatureStore
from app.datastore.evidence_writer import write_evidence
from app.datastore.schema.row_models import EvidenceRow
from app.offline_jobs.common.ee_auth import init_earth_engine
from app.offline_jobs.common.job_base import JobRunSummary, build_arg_parser, configure_logging

# OPEN ITEM: verify against the Earth Engine Data Catalog before relying on this.
ALPHAEARTH_ASSET = "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL"
METHOD_VERSION = "alphaearth-cosine-sim-v1"
COSINE_SIM_CHANGE_THRESHOLD = 0.85  # below this = "changed"; tune against NAIP labels


def _austin_aoi() -> ee.Geometry:
    return ee.Geometry.Rectangle([-98.15, 30.05, -97.45, 30.65])


def cosine_similarity_image(year_a_embedding: ee.Image, year_b_embedding: ee.Image) -> ee.Image:
    dot = year_a_embedding.multiply(year_b_embedding).reduce(ee.Reducer.sum())
    norm_a = year_a_embedding.pow(2).reduce(ee.Reducer.sum()).sqrt()
    norm_b = year_b_embedding.pow(2).reduce(ee.Reducer.sum()).sqrt()
    return dot.divide(norm_a.multiply(norm_b)).rename("cosine_sim")


def changed_mask(cosine_sim: ee.Image) -> ee.Image:
    return cosine_sim.lt(COSINE_SIM_CHANGE_THRESHOLD).rename("changed")


def run(start_date: date, end_date: date, h3_resolution: int, dry_run: bool) -> JobRunSummary:
    settings = get_settings()
    logger = configure_logging()
    summary = JobRunSummary(hazard="landuse")

    if dry_run:
        logger.info("[dry-run] would compute AlphaEarth year-over-year change for %s..%s", start_date, end_date)
        summary.log(logger)
        return summary

    init_earth_engine(settings)
    aoi = _austin_aoi()
    store = BigQueryFeatureStore(settings)

    years = list(range(max(start_date.year, 2017), min(end_date.year, 2025) + 1))
    evidence_rows = []
    for year_a, year_b in zip(years, years[1:]):
        # TODO: load ee.Image(f"{ALPHAEARTH_ASSET}/{year_a}") style assets once
        # the real asset path/naming is confirmed; compute cosine_similarity_image
        # and changed_mask, then reduceRegions per H3 cell for "share changed."
        evidence_rows.append(
            EvidenceRow(
                evidence_id=f"E-landuse-{year_a}-{year_b}",
                hazard="landuse",
                source_product=ALPHAEARTH_ASSET,
                granule_ids=[],
                date_start=date(year_a, 1, 1),
                date_end=date(year_b, 12, 31),
                method_version=METHOD_VERSION,
                values_json={"year_a": year_a, "year_b": year_b},
                license="CC-BY-4.0",
                created_at=datetime.now(timezone.utc),
            )
        )

    write_evidence(store, evidence_rows)
    summary.evidence_rows_written = len(evidence_rows)
    summary.log(logger)
    return summary


def main() -> None:
    parser = build_arg_parser("Land-use change offline job -- AlphaEarth embeddings")
    args = parser.parse_args()
    run(args.start_date, args.end_date, args.h3_resolution, args.dry_run)


if __name__ == "__main__":
    main()
