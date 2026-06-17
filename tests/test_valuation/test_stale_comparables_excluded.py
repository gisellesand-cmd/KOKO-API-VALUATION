"""
Enforces the staleness filter: comparables with
``scraped_at < now - 90 days`` MUST be excluded. Exactly 90 days is
INCLUDED (the rule uses strict ``<``).
"""

# LOAD-BEARING: enforces "Cero datos inventados" -- do NOT skip or delete.

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from freezegun import freeze_time

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

FROZEN_NOW = datetime(2026, 6, 16, tzinfo=timezone.utc)


@pytest.mark.asyncio
@pytest.mark.integration
@freeze_time("2026-06-16")
async def test_only_fresh_comparables_counted(async_session):
    city = CityFactory(slug="tulum", name="Tulum")
    zone = ZoneFactory(slug="aldea-zama", name="Aldea Zama", city=city)
    PropertyTypeFactory(slug="casa", name="Casa")

    fresh_at = datetime(2026, 6, 10, tzinfo=timezone.utc)
    stale_at = datetime(2026, 2, 1, tzinfo=timezone.utc)
    for _ in range(5):
        ComparableFactory(
            city=city, zone=zone, currency="MXN", price_mxn=45000 * 200,
            area_m2=200, price_per_m2_mxn=45000, is_preventa=False, scraped_at=fresh_at,
        )
    for _ in range(5):
        ComparableFactory(
            city=city, zone=zone, currency="MXN", price_mxn=10000 * 200,
            area_m2=200, price_per_m2_mxn=10000, is_preventa=False, scraped_at=stale_at,
        )

    result = await valuate(async_session, **REQUEST)

    assert result["comparables_count"] == 5


@pytest.mark.asyncio
@pytest.mark.integration
@freeze_time("2026-06-16")
async def test_all_stale_returns_insufficient(async_session):
    city = CityFactory(slug="tulum", name="Tulum")
    zone = ZoneFactory(slug="aldea-zama", name="Aldea Zama", city=city)
    PropertyTypeFactory(slug="casa", name="Casa")

    stale_at = datetime(2026, 2, 1, tzinfo=timezone.utc)
    for _ in range(10):
        ComparableFactory(
            city=city, zone=zone, currency="MXN", price_mxn=45000 * 200,
            area_m2=200, price_per_m2_mxn=45000, is_preventa=False, scraped_at=stale_at,
        )

    result = await valuate(async_session, **REQUEST)

    assert result["comparables_count"] == 0
    assert result["confidence"] == "insuficiente"
    assert result["price_median_mxn"] is None


@pytest.mark.asyncio
@pytest.mark.integration
@freeze_time("2026-06-16")
async def test_borderline_exactly_90_days_is_included(async_session):
    """Spec: stale := scraped_at < now - 90d (strict). Exactly 90d is fresh."""
    city = CityFactory(slug="tulum", name="Tulum")
    zone = ZoneFactory(slug="aldea-zama", name="Aldea Zama", city=city)
    PropertyTypeFactory(slug="casa", name="Casa")

    border_at = FROZEN_NOW - timedelta(days=90)
    for _ in range(5):
        ComparableFactory(
            city=city, zone=zone, currency="MXN", price_mxn=45000 * 200,
            area_m2=200, price_per_m2_mxn=45000, is_preventa=False, scraped_at=border_at,
        )

    result = await valuate(async_session, **REQUEST)

    assert result["comparables_count"] == 5
