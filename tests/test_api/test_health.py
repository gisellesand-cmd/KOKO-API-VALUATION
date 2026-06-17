"""
Integration tests for ``GET /health`` — liveness probe.

Rules verified:
  * Returns HTTP 200 with the canonical ``{"status": "ok"}`` body.
  * The liveness probe is intentionally cheap: it must NOT touch the DB.
    We assert this indirectly by hitting the endpoint without seeding any
    data and without relying on the async_session fixture for state.
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_returns_ok(api_client):
    response = await api_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok"}
