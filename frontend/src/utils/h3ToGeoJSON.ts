import { cellToBoundary } from "h3-js";

/** Returns [{ lat, lng }, ...] boundary vertices for an H3 cell, ready to
 * pass to a google.maps.Polygon's `paths` option. */
export function cellBoundaryLatLng(h3Cell: string): google.maps.LatLngLiteral[] {
  return cellToBoundary(h3Cell, false).map(([lat, lng]) => ({ lat, lng }));
}
