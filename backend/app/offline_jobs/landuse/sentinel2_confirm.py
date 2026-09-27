"""Land-use change offline job (part 2): Sentinel-2 confirmation signal.

For cells the AlphaEarth cosine-similarity check flags as changed, compute
an NDVI/NDWI delta between the same two years as an independent
confirmation signal (reduces false positives from AlphaEarth alone).
"""

import ee


def _ndvi(image: ee.Image) -> ee.Image:
    return image.normalizedDifference(["B8", "B4"]).rename("ndvi")


def _ndwi(image: ee.Image) -> ee.Image:
    return image.normalizedDifference(["B3", "B8"]).rename("ndwi")


def annual_composite(year: int, aoi: ee.Geometry) -> ee.Image:
    coll = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(aoi)
        .filterDate(f"{year}-01-01", f"{year}-12-31")
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
    )
    median = coll.median()
    return median.addBands(_ndvi(median)).addBands(_ndwi(median))


def confirm_change(year_a_composite: ee.Image, year_b_composite: ee.Image) -> ee.Image:
    """Absolute NDVI delta as a confirmation signal; larger = more likely a
    real vegetation/land-cover change rather than an AlphaEarth embedding
    artifact."""
    ndvi_delta = year_b_composite.select("ndvi").subtract(year_a_composite.select("ndvi")).abs()
    return ndvi_delta.rename("ndvi_delta")
