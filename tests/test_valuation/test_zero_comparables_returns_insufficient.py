"""
Enforces: when there are zero usable comparables, the engine MUST return
``confidence == "insuficiente"`` and ALL price fields MUST be None.

This is the absolute floor of the "Cero datos inventados" rule: no fallback
to averages, no synthetic numbers, no silent defaults.
"""

# LOAD-BEARING: enforces "Cero datos inventados" -- do NOT skip or delete.

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.services.valuation import ValuationEngine, valuate  # type: ignore
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


@pytest.mark.asyncio
@pytest.mark.integration
async def test_no_comparables_in_db_returns_insufficient(async_session):
    CityFactory(slug="tulum", name="Tulum")

    result = await valuate(async_session, **REQUEST)

    assert result["price_median_mxn"] is None
    assert result["price_p25_mxn"] is None
    assert result["price_p75_mxn"] is None
    assert result["price_per_m2_median_mxn"] is None
    assert result["comparables_count"] == 0
    assert result["confidence"] == "insuficiente"
    note = result["methodology_note"].lower()
    assert "insuficiente" in note or "sin comparables" in note


@pytest.mark.asyncio
@pytest.mark.integration
async def test_zero_returns_none_even_for_known_city_zone(async_session):
    city = CityFactory(slug="tulum", name="Tulum")
    ZoneFactory(slug="aldea-zama", name="Aldea Zama", city=city)
    PropertyTypeFactory(slug="casa", name="Casa")

    result = await valuate(async_session, **REQUEST)

    assert result["price_median_mxn"] is None
    assert result["price_per_m2_median_mxn"] is None
    assert result["comparables_count"] == 0
    assert result["confidence"] == "insuficiente"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_no_invented_numbers_when_only_excluded_comparables(async_session):
    city = CityFactory(slug="tulum", name="Tulum")
    zone = ZoneFactory(slug="aldea-zama", name="Aldea Zama", city=city)
    other_city = CityFactory(slug="cancun", name="Cancun")
    now = datetime.now(timezone.utc)

    # All 5 fail one filter or another.
    ComparableFactory(city=city, zone=zone, is_preventa=True, scraped_at=now)
    ComparableFactory(city=city, zone=zone, is_preventa=True, scraped_at=now)
    ComparableFactory(city=city, zone=zone, scraped_at=now - timedelta(days=120))
    ComparableFactory(city=city, zone=zone, scraped_at=now - timedelta(days=200))
    ComparableFactory(city=other_city, scraped_at=now)

    result = await valuate(async_session, **REQUEST)

    assert result["price_median_mxn"] is None
    assert result["price_p25_mxn"] is None
    assert result["price_p75_mxn"] is None
    assert result["price_per_m2_median_mxn"] is None
    assert result["comparables_count"] == 0
    assert result["confidence"] == "insuficiente"
