from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env lives at the repo root (one level above backend/), not relative to
# whatever directory the process happens to be launched from -- README's
# setup steps run commands from inside backend/, so a bare "env_file=".env""
# would silently miss it.
_REPO_ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_REPO_ROOT_ENV_FILE, extra="ignore")

    # Google Cloud
    gcp_project_id: str = ""
    bq_dataset: str = "landrisk"
    ee_project: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # TypeSafe / Jev -- pin an exact version, never "jev-latest".
    typesafe_api_key: str = ""
    jev_model: str = "jev-1.13.0"
    jev_confidence_threshold: float = 0.6

    # Gemini (LLM report writer)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"

    # NASA Earthdata (subsidence job) -- new requirement, not in the
    # design doc's original provisioned-credential list.
    earthdata_token: str = ""

    # NASA FIRMS (wildfire job) -- new requirement, not in the design
    # doc's original provisioned-credential list.
    firms_map_key: str = ""

    app_env: Literal["local", "dev"] = "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
