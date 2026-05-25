import hashlib
import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ResponseCache:
    """
    Simple in-memory dict cache with TTL.
    Interface designed for Redis drop-in replacement in production.
    
    Key = SHA256 hash of all query inputs combined.
    Value = stored response dict + expiry timestamp.
    """

    def __init__(self, ttl_seconds: int = 604800, max_size: int = 500):
        self._store: dict[str, dict] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size

    def _make_key(self, **inputs) -> str:
        """Deterministic hash of all query inputs."""
        canonical = json.dumps(inputs, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def get(self, **inputs) -> Any | None:
        """Returns cached value or None if missing/expired."""
        key = self._make_key(**inputs)
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.time() > entry["expires_at"]:
            del self._store[key]
            logger.debug(f"Cache expired for key {key[:8]}...")
            return None
        logger.info(f"Cache hit for key {key[:8]}...")
        return entry["value"]

    def set(self, value: Any, **inputs) -> None:
        """Stores value with TTL. Evicts oldest entry if at max size."""
        if len(self._store) >= self._max_size:
            oldest = min(self._store, key=lambda k: self._store[k]["expires_at"])
            del self._store[oldest]
            logger.debug("Cache evicted oldest entry")

        key = self._make_key(**inputs)
        self._store[key] = {
            "value": value,
            "expires_at": time.time() + self._ttl,
        }
        logger.info(f"Cache set for key {key[:8]}...")

    def size(self) -> int:
        return len(self._store)

    def clear(self) -> None:
        self._store.clear()


# Module-level singleton — imported and reused across requests
from app.core.config import get_settings
_settings = get_settings()

cache = ResponseCache(
    ttl_seconds=_settings.cache_ttl_seconds,
    max_size=_settings.cache_max_size,
)