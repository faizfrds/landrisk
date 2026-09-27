# Parcel Risk Report

Turns a US address into a cited, satellite-backed climate-risk report in
under 30 seconds (p95). Pilot metro: Austin, TX. Covers 5 hazards: flood,
ground subsidence, wildfire, extreme heat, and nearby land-use change.

See `Parcel Risk Report — Technical Design Document (1).pdf` for the full
design. This repo is a scaffold: the online request path (API, scoring,
report writing, PDF export) is complete and testable now; the offline
satellite-processing jobs are wired against real SDKs but not yet run
against live data (see "What's not done yet" below).

## Repo layout

- `backend/` — Python/FastAPI. Offline hazard jobs (`app/offline_jobs/`),
  the online report API (`app/api/`, `app/core/`), scoring (`app/scoring/`),
  report writing (`app/reportgen/`), PDF export (`app/pdf/`), and the
  BigQuery data model (`app/datastore/`).
- `frontend/` — TypeScript/React (Vite). Address form, streamed progress,
  report view, and a Google Maps view with toggleable hazard layers.

## Setup

### Prerequisites

1. Copy `.env.example` to `.env` (repo root) and fill in every value.
   Two credentials are new requirements beyond the original provisioned
   set, needed only for the subsidence and wildfire offline jobs:
   - `EARTHDATA_TOKEN` — register free at https://urs.earthdata.nasa.gov/
   - `FIRMS_MAP_KEY` — register free at https://firms.modaps.eosdis.nasa.gov/api/map_key/
2. `gcloud auth application-default login`
3. Confirm Earth Engine is registered for `EE_PROJECT` at
   https://console.cloud.google.com/earth-engine
4. Copy `frontend/.env.example` to `frontend/.env` and fill in
   `VITE_GOOGLE_MAPS_API_KEY`.

### Backend

```
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

WeasyPrint (PDF export) needs native libraries not covered by `pip
install`. On macOS:

```
brew install pango
```

(This installs Cairo and other transitive deps too.) See
https://doc.courtbouillon.org/weasyprint/stable/first_steps.html for other
platforms.

### Frontend

```
cd frontend
npm install
npm run dev
```

## Running the offline jobs

Not required to test the online path (see Verification below) -- these
populate the real feature store from real satellite data:

```
cd backend
python -m app.datastore.schema.create_tables   # once, creates the 4 BigQuery tables
python -m app.offline_jobs.context.run_all --start-date 2015-01-01 --end-date 2026-01-01 --dry-run
```

Drop `--dry-run` once you've confirmed the plan looks right. Manual
downloads required first for two jobs: MTBS burn perimeters into
`backend/data/reference/mtbs/`, and Travis County parcel data into
`backend/data/reference/travis_parcels/` (see the docstrings in
`app/offline_jobs/wildfire/mtbs_burns.py` and
`app/offline_jobs/context/parcels_ingest.py` for where to get them).

## Verification -- "did the scaffold actually work?"

### 1. Hermetic test suite (no credentials, no network)

```
cd backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/ -v
```

Exercises the full online path (geocode → parcel resolution → cache check
→ H3 feature aggregation → Jev scoring with rule-baseline fallback →
report writing → citation validation → PDF render → cache write) against
an in-memory BigQuery fake and fakeredis, including the data-gaps path (one
seeded hazard is deliberately `no_data: true`). Also unit-tests the
citation validator directly (the safety-critical piece that stops the LLM
from inventing or distorting a claim).

### 2. Manual end-to-end smoke test (real BigQuery/Redis, real address)

```
cd backend
python -m app.datastore.schema.create_tables
python -m scripts.seed_bigquery
uvicorn app.main:app --reload &
python -m scripts.smoke_test "301 Congress Ave, Austin, TX"
```

Seeds the same fixture rows the hermetic test uses into your real BigQuery
dev dataset, then drives the real FastAPI app with a real Travis County
address through the real US Census geocoder. Uses real Jev/Gemini calls if
`TYPESAFE_API_KEY`/`GEMINI_API_KEY` are set; otherwise the orchestrator
automatically falls back to the rule baseline and a templated report.
Confirms the PDF endpoint returns non-empty bytes.

### 3. Frontend

```
cd frontend
npm run build   # type-checks + bundles
npm run dev     # then submit an address against a running backend
```

## What's not done yet (by design, this pass)

- Offline jobs are real client code against real SDKs but have not been
  run against live satellite data end-to-end -- several have `TODO`
  markers for the per-cell reduction step (see each job's docstring).
- The 300-parcel labeled evaluation set and the Jev-vs-rule-baseline
  calibration harness (`backend/app/eval/`) -- stubbed only, per the design
  doc this is real work for a later phase, not scaffold work.
- CI/CD, auth, multi-tenant billing, production deploy configs (Terraform,
  Cloud Run manifests, k8s). `docker-compose.yml` is local-dev Redis only.

## Open items to confirm before relying on this in production

- Exact Gemini model id (`gemini-3.6-flash`, taken from the design doc,
  not independently verified against a live model catalog).
- Exact AlphaEarth Earth Engine asset ID (placeholder in
  `app/offline_jobs/landuse/alphaearth_embeddings.py`).
- NASA OPERA DISP-S1 coverage over Travis County specifically (the design
  doc's own called-out risk for the subsidence hazard).
- Travis County parcel data license/redistribution terms, before serving
  parcel geometries beyond local dev.
- The TypeSafe `typesafe_sdk` integration in `app/scoring/` was verified
  against the installed package (0.7.2) during this build -- re-check
  against https://docs.typesafe.ai if you upgrade, since Jev is early
  access and the design doc itself warns that thresholds must be re-tuned
  before any version bump.
