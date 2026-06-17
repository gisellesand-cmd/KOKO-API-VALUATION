# LOAD-BEARING: enforces "Cero datos inventados". Do NOT skip.
"""
Integration tests for ``POST /v1/valuation`` — insufficient-data behaviour.

Rules verified (NON-NEGOTIABLE, per PRD "Cero datos inventados"):
  * When the requested city/zone/property combination has zero comparables
    the API must respond HTTP 200 (NOT 404) with explicit nulls for every
    price_* field, a zero comparables_count, ``confidence == "insuficiente"``,
    and a methodology_note that explains the lack of data.
  * The response body must be valid JSON and conform exactly to the
    insufficient-data schema — no invented numbers, no silent fallbacks.
"""

from __future__ import annotations

import json

import pytest

from tests.factories import (
    PropertyTypeFactory,
    TulumCityFactory,
    ZoneFactory,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_valuation_returns_200_with_nulls_when_no_comparables(
    api_client, async_session, auth_headers
):
    city = TulumCityFactory()
    ZoneFactory(city=city, name="Aldea Zama", slug="aldea-zama")
    PropertyTypeFactory(slug="casa")
    # Deliberately no ComparableFactory calls.

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
    assert body["price_median_mxn"] is None
    assert body["price_p25_mxn"] is None
    assert body["price_p75_mxn"] is None
    assert body["price_per_m2_median_mxn"] is None
    assert body["comparables_count"] == 0
    assert body["confidence"] == "insuficiente"
    assert "methodology_note" in body
    note = body["methodology_note"].lower()
    assert any(token in note for token in ("insuficien", "sin datos", "no hay", "no data"))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_valuation_insufficient_schema_is_exact(
    api_client, async_session, auth_headers
):
    city = TulumCityFactory()
    ZoneFactory(city=city, name="Aldea Zama", slug="aldea-zama")
    PropertyTypeFactory(slug="casa")

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
    # Body must be JSON-parseable round-trip.
    body = json.loads(response.text)
    expected_keys = {
        "price_median_mxn",
        "price_p25_mxn",
        "price_p75_mxn",
        "price_per_m2_median_mxn",
        "comparables_count",
        "confidence",
        "geographic_scope",
        "methodology_note",
        "currency",
        "as_of",
    }
    assert expected_keys.issubset(set(body.keys()))
    assert body["confidence"] == "insuficiente"
    assert body["comparables_count"] == 0
    assert body["currency"] == "MXN"
