"""Context job: FEMA NFHL flood zones -- a reference layer, not a scored
hazard. Per design doc's risk mitigation: show the official FEMA zone
beside satellite-derived flood history, since satellites miss short/urban
floods. Not written to hazard_features; kept as a separate reference table
the report/frontend can display alongside the flood hazard.

Manual download: FEMA NFHL data for Travis County from
https://msc.fema.gov/portal/advanceSearch
"""

from pathlib import Path

import geopandas as gpd

from app.offline_jobs.common.job_base import configure_logging

FEMA_DIR = Path(__file__).parents[3] / "data" / "reference" / "fema_nfhl"


def load_flood_zones() -> gpd.GeoDataFrame:
    candidates = list(FEMA_DIR.glob("*.shp")) + list(FEMA_DIR.glob("*.geojson"))
    if not candidates:
        raise FileNotFoundError(
            f"No FEMA NFHL files found in {FEMA_DIR}. Download from "
            "https://msc.fema.gov/portal/advanceSearch and place them there."
        )
    return gpd.read_file(candidates[0]).to_crs(epsg=4326)


def zone_for_point(lat: float, lon: float, zones: gpd.GeoDataFrame) -> str | None:
    from shapely.geometry import Point

    point = Point(lon, lat)
    matches = zones[zones.geometry.contains(point)]
    if matches.empty:
        return None
    return str(matches.iloc[0].get("FLD_ZONE", "UNKNOWN"))


def main() -> None:
    logger = configure_logging()
    try:
        zones = load_flood_zones()
        logger.info("Loaded %d FEMA flood zone polygons", len(zones))
    except FileNotFoundError as exc:
        logger.warning(str(exc))


if __name__ == "__main__":
    main()
