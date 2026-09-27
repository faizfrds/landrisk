"""Earth Engine initialization shared by the flood, heat, and landuse jobs.

Uses Application Default Credentials (gcloud auth application-default
login) -- no service-account key file. Only offline jobs touch Earth
Engine; the online request path never does.
"""

import ee

from app.config import Settings


def init_earth_engine(settings: Settings) -> None:
    if not settings.ee_project:
        raise RuntimeError(
            "EE_PROJECT is not set. Fill it in .env with the GCP project Earth "
            "Engine is registered against."
        )
    try:
        ee.Initialize(project=settings.ee_project)
    except Exception as exc:  # noqa: BLE001 -- surfaced as a clear setup error
        raise RuntimeError(
            "Earth Engine initialization failed. Confirm: "
            "(1) `gcloud auth application-default login` has been run, "
            f"(2) Earth Engine is registered for project '{settings.ee_project}' at "
            "https://console.cloud.google.com/earth-engine"
        ) from exc
