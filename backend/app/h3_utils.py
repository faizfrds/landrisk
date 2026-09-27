"""H3 helpers shared by offline jobs and the online H3 aggregation step.

Resolution 10 (~0.015 km^2 per cell) is the fixed spatial unit for the whole
feature store, per the design doc.
"""

import h3
from shapely.geometry import Polygon, mapping
from shapely.geometry.base import BaseGeometry

H3_RESOLUTION = 10
DEFAULT_BUFFER_M = 500


def polyfill_geometry(geometry: BaseGeometry, res: int = H3_RESOLUTION) -> list[str]:
    """Return the H3 cell ids covering a shapely geometry (lon/lat, EPSG:4326)."""
    geojson = mapping(geometry)
    return list(h3.geo_to_cells(geojson, res))


def k_ring_for_distance_m(distance_m: int = DEFAULT_BUFFER_M, res: int = H3_RESOLUTION) -> int:
    """Number of k-ring steps needed to cover at least `distance_m` from a cell center."""
    edge_len_m = h3.average_hexagon_edge_length(res, unit="m")
    return max(1, int(distance_m / edge_len_m) + 1)


def buffer_cells(center_cells: list[str], distance_m: int = DEFAULT_BUFFER_M) -> set[str]:
    """Expand a set of cells outward by a k-ring approximating `distance_m`."""
    k = k_ring_for_distance_m(distance_m)
    expanded: set[str] = set()
    for cell in center_cells:
        expanded.update(h3.grid_disk(cell, k))
    return expanded


def cell_boundary(h3_cell: str) -> list[tuple[float, float]]:
    """Boundary vertices of a cell as (lat, lng) pairs."""
    return h3.cell_to_boundary(h3_cell)


def cell_polygon(h3_cell: str) -> Polygon:
    boundary = cell_boundary(h3_cell)
    return Polygon([(lng, lat) for lat, lng in boundary])
