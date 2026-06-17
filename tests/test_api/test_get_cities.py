"""
Integration tests for ``GET /v1/cities``.

Rules verified:
  * Returns a list of cities, alpha-sorted by ``slug``, each with the
    correct ``zone_count``.
  * Empty database yields HTTP 200 with an empty list (NOT 404).
"""

from __future__ import annotations

import pytest

from tests.factories import (
    CancunCityFactory,
    PlayaDelCarmenCityFactory,
    TulumCityFactory,
    ZoneFactory,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_cities_returns_alpha_sorted_with_zone_counts(
    api_client, async_session, auth_headers
):
    tulum = TulumCityFactory()
    cancun = CancunCityFactory()
    playa = PlayaDelCarmenCityFactory()
    for i in range(2):
        ZoneFactory(city=tulum, name=f"Tulum Zone {i}")
    for i in range(3):
        ZoneFactory(city=cancun, name=f"Cancun Zone {i}")
    for i in range(1):
        ZoneFactory(city=playa, name=f"Playa Zone {i}")

    response = await api_client.get("/v1/cities", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list) and len(body) == 3
    slugs = [c["slug"] for c in body]
    assert slugs == sorted(slugs)

    by_slug = {c["slug"]: c for c in body}
    assert by_slug["tulum"]["zone_count"] == 2
    assert by_slug["cancun"]["zone_count"] == 3
    assert by_slug["playa-del-carmen"]["zone_count"] == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_cities_empty_db_returns_empty_list(api_client, auth_headers):
    response = await api_client.get("/v1/cities", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []
