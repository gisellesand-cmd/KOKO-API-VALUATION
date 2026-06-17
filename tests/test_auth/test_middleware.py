from __future__ import annotations

import logging
import re

from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth.middleware import RequestContextMiddleware

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _build_app():
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    return app


def test_middleware_adds_request_id_header():
    client = TestClient(_build_app())
    r = client.get("/ping")
    assert r.status_code == 200
    assert _UUID_RE.match(r.headers["X-Request-ID"])


def test_middleware_logs_caller_when_ip_only(caplog):
    caplog.set_level(logging.INFO, logger="auth.middleware")
    client = TestClient(_build_app())
    client.get("/ping")
    records = [r for r in caplog.records if r.name == "auth.middleware"]
    assert records, "expected at least one auth.middleware log record"
    rec = records[-1]
    assert getattr(rec, "caller", "").startswith("ip:")
    assert getattr(rec, "tier", None) == "public"


def test_middleware_logs_status_and_duration(caplog):
    caplog.set_level(logging.INFO, logger="auth.middleware")
    client = TestClient(_build_app())
    client.get("/ping")
    rec = [r for r in caplog.records if r.name == "auth.middleware"][-1]
    assert getattr(rec, "status_code", None) == 200
    assert getattr(rec, "duration_ms", None) is not None
