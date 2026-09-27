"""Context job: Travis County parcel polygons -> parcels table.

Manual download required: get Travis County parcel data (shapefile or
GeoJSON) and place it under backend/data/reference/travis_parcels/ before
running this job.

OPEN ITEM (flagged in the plan): verify the county's parcel data license /
redistribution terms before serving these geometries beyond local dev --
the design doc calls this out as a real risk ("data licenses" row).

This job also derives each parcel's H3 cell coverage and 500m buffer ring,
which the online path (core/h3_aggregate.py) reads directly rather than
recomputing per-request.
"""

from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd

from app.config import get_settings
from app.datastore.bigquery_client import BigQueryFeatureStore
from app.datastore.schema.row_models import ParcelRow
from app.h3_utils import buffer_cells, polyfill_geometry
from app.offline_jobs.common.job_base import configure_logging

PARCELS_DIR = Path(__file__).parents[3] / "data" / "reference" / "travis_parcels"


def load_parcels() -> gpd.GeoDataFrame:
    candidates = list(PARCELS_DIR.glob("*.shp")) + list(PARCELS_DIR.glob("*.geojson"))
    if not candidates:
        raise FileNotFoundError(
            f"No parcel files found in {PARCELS_DIR}. Download Travis County parcel "
            "data (shapefile or GeoJSON) and place it there."
        )
    gdf = gpd.read_file(candidates[0])
    return gdf.to_crs(epsg=4326)


def ingest(dry_run: bool = False) -> int:
    logger = configure_logging()
    settings = get_settings()

    try:
        parcels = load_parcels()
    except FileNotFoundError as exc:
        logger.warning(str(exc))
        return 0

    logger.info("Loaded %d parcels", len(parcels))
    if dry_run:
        return len(parcels)

    store = BigQueryFeatureStore(settings)
    count = 0
    for _, row in parcels.iterrows():
        geom = row.geometry
        h3_cells = polyfill_geometry(geom)
        cells_500m = list(buffer_cells(h3_cells, distance_m=500))

        parcel_row = ParcelRow(
            parcel_id=str(row.get("parcel_id") or row.get("PROP_ID") or row.name),
            county_fips="48453",  # Travis County, TX
            address=str(row.get("address") or row.get("SITUS_ADDR") or ""),
            geometry_wkt=geom.wkt,
            h3_cells=h3_cells,
            buffer_cells=cells_500m,
            source="travis_county_parcel",
            created_at=datetime.now(timezone.utc),
        )
        store.insert_parcel(
            {
                **parcel_row.model_dump(mode="json", exclude={"geometry_wkt"}),
                "geometry": parcel_row.geometry_wkt,
            }
        )
        count += 1

    logger.info("Wrote %d parcels to BigQuery", count)
    return count


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Context job -- Travis County parcel ingestion")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    ingest(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
