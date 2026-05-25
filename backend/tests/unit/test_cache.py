import time
import pytest
import fakeredis
from app.services.cache import ResponseCache, RedisCache


# ── DictCache (ResponseCache) tests ──────────────────────────────────────────


@pytest.fixture
def dict_cache():
    return ResponseCache(ttl_seconds=60, max_size=10)


def test_dict_get_miss_returns_none(dict_cache):
    assert dict_cache.get(question="anything") is None


def test_dict_set_and_get(dict_cache):
    dict_cache.set({"answer": "TV works"}, question="does TV work?")
    assert dict_cache.get(question="does TV work?") == {"answer": "TV works"}


def test_dict_key_order_independent(dict_cache):
    dict_cache.set({"answer": "yes"}, question="q", sector="FMCG")
    assert dict_cache.get(sector="FMCG", question="q") == {"answer": "yes"}


def test_dict_expired_returns_none():
    c = ResponseCache(ttl_seconds=0, max_size=10)
    c.set({"answer": "x"}, question="q")
    time.sleep(0.01)
    assert c.get(question="q") is None


def test_dict_max_size_evicts_oldest():
    c = ResponseCache(ttl_seconds=3600, max_size=2)
    c.set({"v": 1}, question="q1")
    c.set({"v": 2}, question="q2")
    c.set({"v": 3}, question="q3")
    assert c.size() == 2


def test_dict_clear(dict_cache):
    dict_cache.set({"v": 1}, question="q")
    dict_cache.clear()
    assert dict_cache.size() == 0


# ── RedisCache tests (using fakeredis — no real Redis needed) ─────────────────


@pytest.fixture
def redis_cache():
    client = fakeredis.FakeRedis(decode_responses=True)
    return RedisCache(client=client, ttl_seconds=60)


def test_redis_get_miss_returns_none(redis_cache):
    assert redis_cache.get(question="anything") is None


def test_redis_set_and_get(redis_cache):
    redis_cache.set({"answer": "TV works"}, question="does TV work?")
    assert redis_cache.get(question="does TV work?") == {"answer": "TV works"}


def test_redis_key_order_independent(redis_cache):
    redis_cache.set({"answer": "yes"}, question="q", sector="FMCG")
    assert redis_cache.get(sector="FMCG", question="q") == {"answer": "yes"}


def test_redis_expired_returns_none():
    client = fakeredis.FakeRedis(decode_responses=True)
    c = RedisCache(client=client, ttl_seconds=1)
    c.set({"answer": "x"}, question="q")
    time.sleep(1.1)
    assert c.get(question="q") is None


def test_redis_clear(redis_cache):
    redis_cache.set({"v": 1}, question="q1")
    redis_cache.set({"v": 2}, question="q2")
    redis_cache.clear()
    assert redis_cache.size() == 0


def test_redis_size(redis_cache):
    redis_cache.set({"v": 1}, question="q1")
    redis_cache.set({"v": 2}, question="q2")
    assert redis_cache.size() == 2


def test_redis_get_returns_none_on_connection_error():
    """RedisCache must fail gracefully — never crash the request."""
    import redis
    from unittest.mock import MagicMock

    broken_client = MagicMock(spec=redis.Redis)
    broken_client.get.side_effect = redis.RedisError("connection refused")
    c = RedisCache(client=broken_client, ttl_seconds=60)
    assert c.get(question="anything") is None


def test_redis_set_silently_fails_on_connection_error():
    import redis
    from unittest.mock import MagicMock

    broken_client = MagicMock(spec=redis.Redis)
    broken_client.setex.side_effect = redis.RedisError("connection refused")
    c = RedisCache(client=broken_client, ttl_seconds=60)
    c.set({"v": 1}, question="q")  # must not raise
