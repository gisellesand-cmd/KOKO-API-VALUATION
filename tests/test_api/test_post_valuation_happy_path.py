"""
Integration tests for ``POST /v1/valuation`` — happy path.

Rules verified:
  * With sufficient fresh MXN comparables in the requested zone the API
    returns HTTP 200, a positive integer ``price_median_mxn``, an "alta"
    confidence band, a "zone" geographic_scope, and the canonical MXN
    currency tag.
  * Optional body fields ``bedrooms`` and ``bathrooms`` may be omitted.
"""

from __future__ import annotations

import pytest

from tests.factories import (
    ComparableFactory,
    PropertyTypeFactory,
    TulumCityFactory,
    ZoneFactory,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_valuation_alta_confidence_with_twelve_comparables(
    api_client, async_session, auth_headers
):
    city = TulumCityFactory()
    zone = ZoneFactory(city=city, name="Aldea Zama", slug="aldea-zama")
    prop_type = PropertyTypeFactory(slug="casa")
    for _ in range(12):
        ComparableFactory(city=city, zone=zone, property_type=prop_type)

    response = await api_client.post(
        "/v1/valuation",
        headers=auth_headers,
        json={
            "city_slug": "tulum",
            "zone_slug": "aldea-zama",
            "property_type": "casa",
            "area_m2": 200,
            "bedrooms": 3,
            "bathrooms": 2,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["confidence"] == "alta"
    assert body["comparables_count"] == 12
    assert body["geographic_scope"] == "zone"
    assert body["currency"] == "MXN"
    assert isinstance(body["price_median_mxn"], int) and body["price_median_mxn"] > 0
    assert "methodology_note" in body and body["methodology_note"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_valuation_bedrooms_and_bathrooms_optional(
    api_client, async_session, auth_headers
):
    city = TulumCityFactory()
    zone = ZoneFactory(city=city, name="Aldea Zama", slug="aldea-zama")
    prop_type = PropertyTypeFactory(slug="casa")
    for _ in range(12):
        ComparableFactory(city=city, zone=zone, property_type=prop_type)

    response = await api_client.post(
        "/v1/valuation",
        headers=auth_headers,
        json={
            "city_slug": "tulum",
            "zone_slug": "aldea-zama",
            "property_type": "casa",
            "area_m2": 200,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["currency"] == "MXN"
    assert body["comparables_count"] >= 0
