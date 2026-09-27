"""FastAPI dependency providers. Indirection here is what lets
tests/conftest.py substitute fakes (FakeBigQueryClient, fakeredis) without
touching real BigQuery/Redis in the hermetic smoke test.
"""

import redis
from fastapi import Request

from app.config import get_settings
from app.datastore.bigquery_client import BigQueryFeatureStore, HazardFeatureStore

_bq_singleton: BigQueryFeatureStore | None = None
_redis_singleton: redis.Redis | None = None


def get_bq_client(request: Request) -> HazardFeatureStore:
    override = getattr(request.app.state, "bq_client_override", None)
    if override is not None:
        return override
    global _bq_singleton
    if _bq_singleton is None:
        _bq_singleton = BigQueryFeatureStore(get_settings())
    return _bq_singleton


def get_redis_client(request: Request) -> redis.Redis:
    override = getattr(request.app.state, "redis_client_override", None)
    if override is not None:
        return override
    global _redis_singleton
    if _redis_singleton is None:
        _redis_singleton = redis.Redis.from_url(get_settings().redis_url)
    return _redis_singleton
