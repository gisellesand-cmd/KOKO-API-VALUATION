"""Request context middleware.

Stamps each request with a UUID, captures caller identity (API key id or IP)
and tier, times the request, and emits one structured log line per request.
Adds ``X-Request-ID`` to the response so clients can correlate.
"""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client else "unknown"


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        api_key = getattr(request.state, "api_key", None)
        if api_key is not None and getattr(api_key, "id", None) is not None:
            caller = f"api_key:{api_key.id}"
            tier = getattr(api_key, "tier", "unknown")
        else:
            caller = f"ip:{_client_ip(request)}"
            tier = "public"

        user_agent = request.headers.get("user-agent", "")[:200]
        start = time.perf_counter()
        log_extra = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "caller": caller,
            "tier": tier,
            "user_agent": user_agent,
        }

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "request_failed",
                extra={**log_extra, "duration_ms": duration_ms, "error": str(exc)},
            )
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request",
            extra={
                **log_extra,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response


def install_middleware(app: FastAPI) -> None:
    app.add_middleware(RequestContextMiddleware)
