"""Composite data_version used for the report cache key and reports table.

hazard_features is keyed by a per-hazard data_version (see data_version.py),
but the design doc's cache key and `reports.data_version` use a single
value. Reconciliation: combine the current max data_version of each of the
5 hazards into one short hash, refreshed every 5 minutes via Redis so we
don't hit BigQuery on every request.
"""

from __future__ import annotations

import hashlib

import redis

from app.datastore.bigquery_client import HazardFeatureStore

HAZARDS = ["flood", "subsidence", "wildfire", "heat", "landuse"]
CACHE_KEY = "current_versions"
CACHE_TTL_SECONDS = 300


def _compute_composite(per_hazard_versions: dict[str, str]) -> str:
    joined = "|".join(per_hazard_versions.get(h, "none") for h in HAZARDS)
    return hashlib.sha256(joined.encode()).hexdigest()[:12]


def current_composite_version(store: HazardFeatureStore, redis_client: redis.Redis) -> str:
    cached = redis_client.hgetall(CACHE_KEY)
    if cached:
        decoded = {k.decode(): v.decode() for k, v in cached.items()}
        if all(h in decoded for h in HAZARDS):
            return _compute_composite(decoded)

    per_hazard_versions = {h: store.get_max_data_version(h) or "none" for h in HAZARDS}
    pipe = redis_client.pipeline()
    pipe.hset(CACHE_KEY, mapping=per_hazard_versions)
    pipe.expire(CACHE_KEY, CACHE_TTL_SECONDS)
    pipe.execute()

    return _compute_composite(per_hazard_versions)
