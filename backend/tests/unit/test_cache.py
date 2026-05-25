import time
import pytest
from app.services.cache import ResponseCache


@pytest.fixture
def cache():
    return ResponseCache(ttl_seconds=60, max_size=10)


def test_get_miss_returns_none(cache):
    result = cache.get(question="anything")
    assert result is None


def test_set_and_get_returns_value(cache):
    cache.set({"answer": "TV works"}, question="does TV work?")
    result = cache.get(question="does TV work?")
    assert result == {"answer": "TV works"}


def test_cache_key_is_order_independent(cache):
    cache.set({"answer": "yes"}, question="q", sector="FMCG")
    result = cache.get(sector="FMCG", question="q")
    assert result == {"answer": "yes"}


def test_expired_entry_returns_none(cache):
    short_cache = ResponseCache(ttl_seconds=0, max_size=10)
    short_cache.set({"answer": "x"}, question="q")
    time.sleep(0.01)
    assert short_cache.get(question="q") is None


def test_max_size_evicts_oldest(cache):
    small_cache = ResponseCache(ttl_seconds=3600, max_size=2)
    small_cache.set({"v": 1}, question="q1")
    small_cache.set({"v": 2}, question="q2")
    small_cache.set({"v": 3}, question="q3")
    assert small_cache.size() == 2


def test_clear_empties_cache(cache):
    cache.set({"v": 1}, question="q")
    cache.clear()
    assert cache.size() == 0
