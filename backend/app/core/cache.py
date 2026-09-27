"""Report cache: Redis key report:{parcel_id}:{data_version} -> full report
JSON blob (not just an id) so a cache hit skips the BigQuery round trip
entirely, to hit the <1s cached-report latency target.
"""

import json

import redis

CACHE_TTL_SECONDS = 60 * 60 * 24 * 7  # 1 week; a new data release changes
                                       # the composite version, which
                                       # naturally invalidates old entries


def _cache_key(parcel_id: str, data_version: str) -> str:
    return f"report:{parcel_id}:{data_version}"


def get_cached_report(redis_client: redis.Redis, parcel_id: str, data_version: str) -> dict | None:
    raw = redis_client.get(_cache_key(parcel_id, data_version))
    return json.loads(raw) if raw else None


def set_cached_report(redis_client: redis.Redis, parcel_id: str, data_version: str, report: dict) -> None:
    redis_client.set(_cache_key(parcel_id, data_version), json.dumps(report), ex=CACHE_TTL_SECONDS)
