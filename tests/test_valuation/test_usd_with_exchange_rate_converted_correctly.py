"""
Enforces: when a valid ``ExchangeRate`` row exists for USD_MXN, the engine
MUST convert USD comparables exactly using that row's rate, and use the
MOST RECENT applicable rate when multiple exist.

The formula MUST be: ``price_per_m2_mxn = (price_usd * rate) / area_m2``.
"""

# LOAD-BEARING: enforces "Cero datos inventados" -- do NOT skip or delete.

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.services.valuation import valuate  # type: ignore
from tests.factories import (  # type: ignore
    CityFactory,
    ComparableFactory,
    ExchangeRateFactory,
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
async def test_usd_converted_at_exact_rate_18_5(async_session):
    city = CityFactory(slug="tulum", name="Tulum")
    zone = ZoneFactory(slug="aldea-zama", name="Aldea Zama", city=city)
    PropertyTypeFactory(slug="casa", name="Casa")
    now = datetime.now(timezone.utc)
    ExchangeRateFactory(currency_pair="USD_MXN", rate=18.5, as_of=now - timedelta(days=1))

    for _ in range(5):
        ComparableFactory(
            city=city, zone=zone, currency="USD", price_usd=100000,
            area_m2=100, is_preventa=False, scraped_at=now,
        )

    result = await valuate(async_session, **REQUEST)

    # (100000 * 18.5) / 100 = 18500 MXN/m2.
    assert result["price_per_m2_median_mxn"] == pytest.approx(18500, abs=1)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_usd_converted_at_rate_20(async_session):
    city = CityFactory(slug="tulum", name="Tulum")
    zone = ZoneFactory(slug="aldea-zama", name="Aldea Zama", city=city)
    PropertyTypeFactory(slug="casa", name="Casa")
    now = datetime.now(timezone.utc)
    ExchangeRateFactory(currency_pair="USD_MXN", rate=20.0, as_of=now - timedelta(days=1))

    for _ in range(5):
        ComparableFactory(
            city=city, zone=zone, currency="USD", price_usd=200000,
            area_m2=200, is_preventa=False, scraped_at=now,
        )

    result = await valuate(async_session, **REQUEST)

    # (200000 * 20.0) / 200 = 20000 MXN/m2.
    assert result["price_per_m2_median_mxn"] == pytest.approx(20000, abs=1)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_most_recent_rate_is_used_when_multiple_rows_exist(async_session):
    city = CityFactory(slug="tulum", name="Tulum")
    zone = ZoneFactory(slug="aldea-zama", name="Aldea Zama", city=city)
    PropertyTypeFactory(slug="casa", name="Casa")
    now = datetime.now(timezone.utc)

    ExchangeRateFactory(currency_pair="USD_MXN", rate=15.0, as_of=now - timedelta(days=30))
    ExchangeRateFactory(currency_pair="USD_MXN", rate=17.0, as_of=now - timedelta(days=10))
    ExchangeRateFactory(currency_pair="USD_MXN", rate=19.0, as_of=now - timedelta(days=1))

    for _ in range(5):
        ComparableFactory(
            city=city, zone=zone, currency="USD", price_usd=100000,
            area_m2=100, is_preventa=False, scraped_at=now,
        )

    result = await valuate(async_session, **REQUEST)

    # Must use 19.0 (most recent): (100000 * 19) / 100 = 19000.
    assert result["price_per_m2_median_mxn"] == pytest.approx(19000, abs=1)
