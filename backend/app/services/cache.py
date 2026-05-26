import hashlib
import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ResponseCache:
    """
    In-memory dict cache with TTL and max-size eviction.
    Used in development and CI (no Redis required).
    Interface is identical to RedisCache for drop-in use.
    """

    def __init__(self, ttl_seconds: int = 604800, max_size: int = 500):
        self._store: dict[str, dict] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size

    def _make_key(self, **inputs: Any) -> str:
        canonical = json.dumps(inputs, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def get(self, **inputs: Any) -> Any | None:
        key = self._make_key(**inputs)
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.time() > entry["expires_at"]:
            del self._store[key]
            return None
        logger.debug(f"Cache hit: {key[:8]}")
        return entry["value"]

    def set(self, value: Any, **inputs: Any) -> None:
        if len(self._store) >= self._max_size:
            oldest = min(self._store, key=lambda k: self._store[k]["expires_at"])
            del self._store[oldest]
        key = self._make_key(**inputs)
        self._store[key] = {"value": value, "expires_at": time.time() + self._ttl}
        logger.debug(f"Cache set: {key[:8]}")

    def size(self) -> int:
        return len(self._store)

    def clear(self) -> None:
        self._store.clear()


class RedisCache:
    """
    Redis-backed cache with TTL.
    Accepts any redis.Redis-compatible client — use redis.from_url in
    production, fakeredis.FakeRedis in tests.
    Fails gracefully on connection errors — never raises to the caller.
    """

    _PREFIX = "tv_advisor:"

    def __init__(self, client: Any, ttl_seconds: int = 604800):
        self._client = client
        self._ttl = ttl_seconds

    def _make_key(self, **inputs: Any) -> str:
        canonical = json.dumps(inputs, sort_keys=True)
        hash_ = hashlib.sha256(canonical.encode()).hexdigest()
        return f"{self._PREFIX}{hash_}"

    def get(self, **inputs: Any) -> Any | None:
        import redis as redis_lib

        try:
            raw = self._client.get(self._make_key(**inputs))
            if raw is None:
                return None
            logger.debug("Redis cache hit")
            return json.loads(raw)
        except redis_lib.RedisError as e:
            logger.error(f"Redis get failed: {e}")
            return None

    def set(self, value: Any, **inputs: Any) -> None:
        import redis as redis_lib

        try:
            self._client.setex(self._make_key(**inputs), self._ttl, json.dumps(value))
            logger.debug("Redis cache set")
        except redis_lib.RedisError as e:
            logger.error(f"Redis set failed: {e}")

    def size(self) -> int:
        import redis as redis_lib

        try:
            return sum(1 for _ in self._client.scan_iter(f"{self._PREFIX}*"))
        except redis_lib.RedisError:
            return 0

    def clear(self) -> None:
        import redis as redis_lib

        try:
            keys = list(self._client.scan_iter(f"{self._PREFIX}*"))
            if keys:
                self._client.delete(*keys)
        except redis_lib.RedisError as e:
            logger.error(f"Redis clear failed: {e}")


def _make_cache() -> ResponseCache | RedisCache:
    """Factory: returns RedisCache if REDIS_URL is set, else ResponseCache."""
    from app.core.config import get_settings

    s = get_settings()
    if s.redis_enabled:
        import redis

        client = redis.from_url(s.redis_url, decode_responses=True)
        logger.info(f"Cache backend: Redis ({s.redis_url})")
        return RedisCache(client=client, ttl_seconds=s.cache_ttl_seconds)
    logger.info("Cache backend: in-memory dict")
    return ResponseCache(ttl_seconds=s.cache_ttl_seconds, max_size=s.cache_max_size)


cache = _make_cache()


def check_redis_status() -> str:
    """Returns 'ok', 'disabled', or 'unavailable'. Safe to call at any time."""
    from app.core.config import get_settings

    s = get_settings()
    if not s.redis_enabled:
        return "disabled"
    if not isinstance(cache, RedisCache):
        return "disabled"
    import redis as redis_lib

    try:
        cache._client.ping()
        return "ok"
    except redis_lib.RedisError:
        return "unavailable"
