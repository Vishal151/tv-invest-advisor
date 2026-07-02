from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.config import get_settings


def rate_limit_key(request: Request) -> str:
    """Real client IP for rate limiting.

    Behind the compose nginx proxy every request arrives from the proxy's
    address, so keying on the socket collapses all clients into one shared
    bucket. Use the first X-Forwarded-For hop instead — but only when
    TRUST_PROXY_HEADERS says the proxy is trusted, because the header is
    client-spoofable in direct deployments.
    """
    if get_settings().trust_proxy_headers:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=rate_limit_key)
