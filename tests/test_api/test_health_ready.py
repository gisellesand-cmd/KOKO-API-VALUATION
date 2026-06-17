"""
Integration tests for ``GET /health/ready`` — readiness probe.

Rules verified:
  * When all dependencies are healthy the endpoint returns HTTP 200 with
    ``status: ready``, ``db: ok``, ``redis: ok``.
  * If the DB session dependency raises, the endpoint must surface HTTP 503
    with ``db: "error"`` so that orchestrators (Kubernetes / Render / Fly)
    can stop routing traffic to the pod.
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_ready_all_green(api_client, auth_headers):
    response = await api_client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body.get("status") == "ready"
    assert body.get("db") == "ok"
    assert body.get("redis") == "ok"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_ready_returns_503_when_db_down(api_client):
    from app.main import app  # type: ignore
    from app.db.session import get_session  # type: ignore

    async def _broken_session():
        raise RuntimeError("simulated DB outage")
        yield  # pragma: no cover - generator contract

    app.dependency_overrides[get_session] = _broken_session
    try:
        response = await api_client.get("/health/ready")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert response.status_code == 503
    body = response.json()
    assert body.get("db") == "error"
