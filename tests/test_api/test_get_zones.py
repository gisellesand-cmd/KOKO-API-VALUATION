"""
Integration tests for ``GET /v1/cities/{slug}/zones``.

Rules verified:
  * Returns the list of zones for a known city; slugs match what was seeded.
  * Unknown city slug returns HTTP 404.
"""

from __future__ import annotations

import pytest

from tests.factories import TulumCityFactory, ZoneFactory


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_zones_for_known_city(api_client, async_session, auth_headers):
    city = TulumCityFactory()
    expected_slugs = {"aldea-zama", "la-veleta", "region-15", "holistika"}
    for name, slug in [
        ("Aldea Zama", "aldea-zama"),
        ("La Veleta", "la-veleta"),
        ("Region 15", "region-15"),
        ("Holistika", "holistika"),
    ]:
        ZoneFactory(city=city, name=name, slug=slug)

    response = await api_client.get("/v1/cities/tulum/zones", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 4
    assert {z["slug"] for z in body} == expected_slugs


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_zones_for_unknown_city_returns_404(api_client, auth_headers):
    response = await api_client.get("/v1/cities/unknown/zones", headers=auth_headers)
    assert response.status_code == 404
    assert "detail" in response.json()
