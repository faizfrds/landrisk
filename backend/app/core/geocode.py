"""US Census Geocoder client -- free, no API key required."""

from dataclasses import dataclass

import httpx

CENSUS_GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"


@dataclass
class GeocodeResult:
    lat: float
    lon: float
    matched_address: str


class GeocodeError(Exception):
    pass


async def geocode_address(address: str) -> GeocodeResult:
    params = {"address": address, "benchmark": "Public_AR_Current", "format": "json"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(CENSUS_GEOCODER_URL, params=params)
        resp.raise_for_status()

    matches = resp.json().get("result", {}).get("addressMatches", [])
    if not matches:
        raise GeocodeError(f"No geocode match for address: {address!r}")

    best = matches[0]
    coords = best["coordinates"]
    return GeocodeResult(
        lat=float(coords["y"]),
        lon=float(coords["x"]),
        matched_address=best["matchedAddress"],
    )
