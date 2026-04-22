"""
Rate limiting via slowapi (Flask-Limiter port for Starlette/FastAPI).

Backed by Redis so counters survive API restarts and are shared between uvicorn
workers. Key policy (audit §2.5):

    /register  -> settings.REGISTER_RATE_LIMIT_PER_IP  per remote addr
    /resend    -> settings.RESEND_RATE_LIMIT_PER_IP    per remote addr
    /verify    -> settings.VERIFY_RATE_LIMIT_PER_IP    per remote addr

We deliberately key by *direct* remote address (not X-Forwarded-For) unless a
trusted proxy is configured — prevents spoofing via the header.
"""

from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urlparse

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger(__name__)


def _resolve_storage_uri() -> str:
    """
    Compute Redis DB for slowapi storage. We use DB 4 to avoid collisions with
    the main cache (DB 0), celery broker (DB 1), celery backend (DB 2).
    """
    if settings.RATE_LIMIT_STORAGE_URL:
        return settings.RATE_LIMIT_STORAGE_URL
    parsed = urlparse(settings.REDIS_URL)
    # replace db number (path "/0") with "/4"
    return parsed._replace(path="/4").geturl()


def _key_func(request: Request) -> str:
    """
    Limit key = direct client IP. Using `get_remote_address` which reads
    request.client.host (not user-controllable).
    """
    return get_remote_address(request)


limiter = Limiter(
    key_func=_key_func,
    storage_uri=_resolve_storage_uri(),
    strategy="fixed-window",
    enabled=settings.RATE_LIMIT_ENABLED,
)


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """
    Uniform 429 response: no information leaked about limit window (audit §2.5
    on enumeration). Minimum retry guidance only.
    """
    logger.warning(
        "rate_limit.exceeded path=%s ip=%s limit=%s",
        request.url.path,
        _key_func(request),
        getattr(exc, "detail", ""),
    )
    return JSONResponse(
        status_code=429,
        content={"detail": "Слишком много запросов. Попробуйте позже."},
        headers={"Retry-After": "60"},
    )
