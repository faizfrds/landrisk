"""Runs the real FastAPI app against the hermetic in-memory feature store
(the same FakeBigQueryClient the test suite uses) instead of real
BigQuery -- for a fast local demo of the online path without waiting on
live GCP calls. Real local Redis is still used for the cache; real
Jev/Gemini calls happen if TYPESAFE_API_KEY/GEMINI_API_KEY are set (with
automatic fallback to the rule baseline / templated report on any
failure, per the design's AI-layer resilience).

This is demo tooling, not part of the two documented verification paths
in the README (hermetic pytest suite, and the real-BigQuery manual smoke
test) -- it exists for exercising the app in a browser quickly.

Usage:
    PYTHONPATH=. python -m scripts.run_demo
"""

import uvicorn

from app.main import app
from tests.conftest import FakeBigQueryClient

app.state.bq_client_override = FakeBigQueryClient()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
