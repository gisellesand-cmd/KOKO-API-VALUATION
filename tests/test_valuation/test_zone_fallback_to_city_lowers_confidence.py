"""
Enforces the zone -> city fallback rule: when a zone has zero comparables,
the engine falls back to the city scope but ALWAYS drops one confidence
bucket. Insufficient at city remains insufficient -- never invented.
"""

# LOAD-BEARING: enforces "Cero datos inventados" -- do NOT skip or delete.

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services.valuation import valuate  # type: ignore
from tests.factories import (  # type: ignore
    CityFactory,
    ComparableFactory,
    PropertyTypeFactory,
    ZoneFactory,
)


REQUEST = {
    "city_slug": "tulum",
    "zone_slug": "aldea-zama",
    "property_type": "casa",
    "area_m2": 200,
    "bedrooms": 3,
    "bathrooms": 2,
}


def _seed_city_with_n_comparables(city, other_zone, n):
    now = datetime.now(timezone.utc)
    for i in range(n):
        ComparableFactory(
            city=city,
            zone=other_zone,
            currency="MXN",
            price_mxn=(40000 + i * 1000) * 200,
            area_m2=200,
            price_per_m2_mxn=40000 + i * 1000,
            is_preventa=False,
            scraped_at=now,
        )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_fallback_drops_alta_to_media(async_session):
    city = CityFactory(slug="tulum", name="Tulum")
    ZoneFactory(slug="aldea-zama", name="Aldea Zama", city=city)
    other_zone = ZoneFactory(slug="la-veleta", name="La Veleta", city=city)
    PropertyTypeFactory(slug="casa", name="Casa")
    _seed_city_with_n_comparables(city, other_zone, 10)

    result = await valuate(async_session, **REQUEST)

    assert result["geographic_scope"] == "city"
    assert result["comparables_count"] == 10
    assert result["confidence"] == "media"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_fallback_drops_media_to_baja(async_session):
    city = CityFactory(slug="tulum", name="Tulum")
    ZoneFactory(slug="aldea-zama", name="Aldea Zama", city=city)
    other_zone = ZoneFactory(slug="la-veleta", name="La Veleta", city=city)
    PropertyTypeFactory(slug="casa", name="Casa")
    _seed_city_with_n_comparables(city, other_zone, 5)

    result = await valuate(async_session, **REQUEST)

    assert result["geographic_scope"] == "city"
    assert result["comparables_count"] == 5
    assert result["confidence"] == "baja"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_fallback_drops_baja_to_insufficient(async_session):
    city = CityFactory(slug="tulum", name="Tulum")
    ZoneFactory(slug="aldea-zama", name="Aldea Zama", city=city)
    other_zone = ZoneFactory(slug="la-veleta", name="La Veleta", city=city)
    PropertyTypeFactory(slug="casa", name="Casa")
    _seed_city_with_n_comparables(city, other_zone, 3)

    result = await valuate(async_session, **REQUEST)

    assert result["confidence"] == "insuficiente"
    assert result["price_median_mxn"] is None
