"""Rate-limit key derivation.

Behind the compose nginx proxy every request reaches uvicorn from the proxy's
IP, so keying on the socket address collapses all clients into one shared
bucket. The key function must use X-Forwarded-For — but only when the
deployment explicitly says the proxy is trusted, otherwise the header is
client-spoofable.
"""

from unittest.mock import MagicMock

from app.core.config import get_settings
from app.core.limiter import rate_limit_key


def _make_request(client_host: str = "10.0.0.5", xff: str | None = None) -> MagicMock:
    request = MagicMock()
    request.client.host = client_host
    request.headers = {"X-Forwarded-For": xff} if xff else {}
    return request


def test_key_ignores_forwarded_header_by_default(monkeypatch):
    """Without TRUST_PROXY_HEADERS the header is spoofable — must be ignored."""
    monkeypatch.setattr(get_settings(), "trust_proxy_headers", False)
    request = _make_request(xff="1.2.3.4")
    assert rate_limit_key(request) == "10.0.0.5"


def test_key_uses_first_forwarded_hop_behind_trusted_proxy(monkeypatch):
    monkeypatch.setattr(get_settings(), "trust_proxy_headers", True)
    request = _make_request(client_host="172.18.0.2", xff="1.2.3.4, 172.18.0.2")
    assert rate_limit_key(request) == "1.2.3.4"


def test_key_falls_back_to_remote_address_without_header(monkeypatch):
    monkeypatch.setattr(get_settings(), "trust_proxy_headers", True)
    request = _make_request()
    assert rate_limit_key(request) == "10.0.0.5"
