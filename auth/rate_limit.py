"""Tier-based rate limiting.

Uses the ``limits`` library directly (slowapi's underlying engine) for a
clean ``hit``/``get_window_stats`` API. Redis is used when ``REDIS_URL`` is
set; otherwise we fall back to in-memory storage so dev works without a
broker. The in-memory fallback is process-local — fine for a single dev
worker, NOT for production with multiple workers.
"""

from __future__ import annotations

import logging
import os
from typing import Callable, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from limits import parse
from limits.storage import MemoryStorage, storage_from_string
from limits.strategies import MovingWindowRateLimiter

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    _SLOWAPI_AVAILABLE = True
except ImportError:
    _SLOWAPI_AVAILABLE = False

    class RateLimitExceeded(Exception):
        pass

logger = logging.getLogger(__name__)


DEFAULT_TIER_LIMITS: dict[str, str] = {
    "public": "20/hour",
    "free": "100/day",
    "paid": "10000/day",
}


def _build_storage():
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        logger.info("REDIS_URL unset; using in-memory rate-limit storage")
        return MemoryStorage()
    try:
        storage = storage_from_string(redis_url)
        # Probe the connection so we fail fast on bad URLs rather than at
        # first request.
        storage.check()
        return storage
    except Exception as exc:
        logger.warning(
            "Redis unavailable (%s); falling back to in-memory rate-limit storage. "
            "Limits will NOT be shared across workers.",
            exc,
        )
        return MemoryStorage()


_storage = _build_storage()
_strategy = MovingWindowRateLimiter(_storage)


def _get_caller_identity(request: Request) -> str:
    api_key = getattr(request.state, "api_key", None)
    if api_key is not None and getattr(api_key, "id", None) is not None:
        return f"apikey:{api_key.id}"
    return f"ip:{_client_ip(request)}"


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client else "unknown"


def _resolve_tier_dep() -> Callable:
    # Late import so this module is independently importable in unit tests
    # that don't pull in the full dependency graph.
    try:
        from auth.dependencies import get_caller_tier
        return get_caller_tier
    except ImportError:
        def _fallback() -> str:
            return "public"
        return _fallback


def rate_limit(per_tier: Optional[dict[str, str]] = None):
    """Return a FastAPI dependency that enforces a tier-based limit.

    Use it via ``Depends(rate_limit())`` on a route or router. The limit is
    chosen by the caller's tier ("public" / "free" / "paid"); identity is the
    API key id when authenticated, else the client IP.
    """
    limits_map = {**DEFAULT_TIER_LIMITS, **(per_tier or {})}
    tier_dep = _resolve_tier_dep()

    async def _dependency(
        request: Request,
        tier: str = Depends(tier_dep),
    ) -> None:
        limit_string = limits_map.get(tier) or limits_map.get("public") or "100/day"
        item = parse(limit_string)
        identity = _get_caller_identity(request)

        if not _strategy.hit(item, identity):
            reset_time, _remaining = _strategy.get_window_stats(item, identity)
            import time
            retry_after = max(1, int(reset_time - time.time()))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: {limit_string}",
                headers={"Retry-After": str(retry_after)},
            )

    return _dependency


def init_rate_limiter(app: FastAPI) -> None:
    """Attach a slowapi Limiter and exception handler to the app.

    The Limiter object is stored on ``app.state`` so route-level
    ``@limiter.limit(...)`` decorators can be added later if needed. The
    dependency-based ``rate_limit()`` above does not rely on it — it uses
    the module-level ``_strategy`` directly.
    """
    if not _SLOWAPI_AVAILABLE:
        logger.warning("slowapi not installed; skipping Limiter setup")
        return

    limiter = Limiter(key_func=_get_caller_identity)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
