"""Resolves a geocoded point to a parcel polygon, falling back to a 30m
point buffer when no parcel exists -- per design doc requirement #1.
"""

from dataclasses import dataclass

from shapely.geometry import Point

from app.core.geocode import GeocodeResult
from app.datastore.bigquery_client import HazardFeatureStore
from app.h3_utils import buffer_cells, polyfill_geometry

POINT_BUFFER_RADIUS_M = 30


@dataclass
class Parcel:
    parcel_id: str
    geometry_wkt: str
    h3_cells: list[str]
    buffer_cells: list[str]
    source: str


def _point_buffer_parcel(lat: float, lon: float) -> Parcel:
    # Rough degrees-per-meter at mid-latitudes; fine for a 30m fallback buffer.
    deg_per_m = 1 / 111_000
    point = Point(lon, lat)
    buffered = point.buffer(POINT_BUFFER_RADIUS_M * deg_per_m)
    h3_cells = polyfill_geometry(buffered)
    cells_500m = list(buffer_cells(h3_cells, distance_m=500))
    return Parcel(
        parcel_id=f"pointbuf:{lat:.6f}:{lon:.6f}",
        geometry_wkt=buffered.wkt,
        h3_cells=h3_cells,
        buffer_cells=cells_500m,
        source="point_buffer_fallback",
    )


def resolve_parcel(geocode_result: GeocodeResult, store: HazardFeatureStore) -> Parcel:
    row = store.find_parcel_containing(geocode_result.lat, geocode_result.lon)
    if row is not None:
        return Parcel(
            parcel_id=row["parcel_id"],
            geometry_wkt=row.get("geometry", ""),
            h3_cells=row.get("h3_cells") or [],
            buffer_cells=row.get("buffer_cells") or [],
            source=row.get("source", "travis_county_parcel"),
        )
    return _point_buffer_parcel(geocode_result.lat, geocode_result.lon)
