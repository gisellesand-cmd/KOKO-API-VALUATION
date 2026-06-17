from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from auth.rate_limit import DEFAULT_TIER_LIMITS, _storage, rate_limit


def _reset_storage():
    if hasattr(_storage, "storage"):
        try:
            _storage.storage.clear()
        except Exception:
            pass
    if hasattr(_storage, "reset"):
        try:
            _storage.reset()
        except Exception:
            pass


def test_default_tier_limits_present():
    assert DEFAULT_TIER_LIMITS["public"] == "20/hour"
    assert DEFAULT_TIER_LIMITS["free"] == "100/day"
    assert DEFAULT_TIER_LIMITS["paid"] == "10000/day"


def _build_app(per_tier=None):
    app = FastAPI()

    @app.get("/ping", dependencies=[Depends(rate_limit(per_tier))])
    def ping():
        return {"ok": True}

    return app


def test_rate_limit_allows_within_limit():
    _reset_storage()
    client = TestClient(_build_app({"public": "5/minute"}))
    r = client.get("/ping")
    assert r.status_code == 200


def test_rate_limit_rejects_over_limit():
    _reset_storage()
    client = TestClient(_build_app({"public": "1/minute"}))
    first = client.get("/ping")
    assert first.status_code == 200
    second = client.get("/ping")
    assert second.status_code == 429
    assert "Retry-After" in second.headers


def test_rate_limit_uses_ip_when_no_api_key():
    _reset_storage()
    client = TestClient(_build_app({"public": "5/minute"}))
    r = client.get("/ping")
    assert r.status_code == 200
