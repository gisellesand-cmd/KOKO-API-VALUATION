"""
Integration tests for ``POST /v1/valuation`` — unknown city / zone slugs.

Rules verified:
  * Posting a ``city_slug`` that does not exist returns HTTP 404 with a
    ``detail`` message that references the offending slug.
  * Posting a valid city with a non-existent ``zone_slug`` returns HTTP 404
    with a ``detail`` message that mentions the zone.
"""

from __future__ import annotations

import pytest

from tests.factories import (
    PropertyTypeFactory,
    TulumCityFactory,
    ZoneFactory,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unknown_city_returns_404(api_client, async_session, auth_headers):
    TulumCityFactory()
    PropertyTypeFactory(slug="casa")

    response = await api_client.post(
        "/v1/valuation",
        headers=auth_headers,
        json={
            "city_slug": "guadalajara",
            "property_type": "casa",
            "area_m2": 200,
        },
    )

    assert response.status_code == 404
    body = response.json()
    assert "detail" in body
    assert "guadalajara" in body["detail"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unknown_zone_returns_404(api_client, async_session, auth_headers):
    city = TulumCityFactory()
    ZoneFactory(city=city, name="Aldea Zama", slug="aldea-zama")
    PropertyTypeFactory(slug="casa")

    response = await api_client.post(
        "/v1/valuation",
        headers=auth_headers,
        json={
            "city_slug": "tulum",
            "zone_slug": "does-not-exist",
            "property_type": "casa",
            "area_m2": 200,
        },
    )

    assert response.status_code == 404
    body = response.json()
    assert "detail" in body
    assert "zone" in body["detail"].lower() or "does-not-exist" in body["detail"].lower()
