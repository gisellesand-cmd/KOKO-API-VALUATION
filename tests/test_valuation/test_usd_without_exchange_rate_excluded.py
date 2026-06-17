"""
Enforces: USD-priced comparables MUST be excluded when no valid
``ExchangeRate`` row exists for USD_MXN at/after the comparable's
``scraped_at``. The engine MUST NEVER silently apply a default rate
(no 20.0, no anything). This is core to "Cero datos inventados".
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


@pytest.mark.asyncio
@pytest.mark.integration
async def test_all_usd_without_rate_returns_insufficient(async_session):
    city = CityFactory(slug="tulum", name="Tulum")
    zone = ZoneFactory(slug="aldea-zama", name="Aldea Zama", city=city)
    PropertyTypeFactory(slug="casa", name="Casa")
    now = datetime.now(timezone.utc)

    for _ in range(5):
        ComparableFactory(
            city=city, zone=zone, currency="USD", price_usd=100000,
            area_m2=100, is_preventa=False, scraped_at=now,
        )

    result = await valuate(async_session, **REQUEST)

    assert result["comparables_count"] == 0
    assert result["price_median_mxn"] is None
    assert result["price_per_m2_median_mxn"] is None
    assert result["confidence"] == "insuficiente"
    note = result["methodology_note"].lower()
    assert "tipo de cambio" in note or "exchange rate" in note


@pytest.mark.asyncio
@pytest.mark.integration
async def test_mxn_counted_usd_dropped_when_no_rate(async_session):
    city = CityFactory(slug="tulum", name="Tulum")
    zone = ZoneFactory(slug="aldea-zama", name="Aldea Zama", city=city)
    PropertyTypeFactory(slug="casa", name="Casa")
    now = datetime.now(timezone.utc)

    for ppm in [44000, 45000, 46000, 47000, 48000]:
        ComparableFactory(
            city=city, zone=zone, currency="MXN", price_mxn=ppm * 200,
            area_m2=200, price_per_m2_mxn=ppm, is_preventa=False, scraped_at=now,
        )
    for _ in range(5):
        ComparableFactory(
            city=city, zone=zone, currency="USD", price_usd=100000,
            area_m2=100, is_preventa=False, scraped_at=now,
        )

    result = await valuate(async_session, **REQUEST)

    assert result["comparables_count"] == 5
    assert result["confidence"] == "media"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_no_hardcoded_default_rate_is_used(async_session):
    """If the engine silently used 20.0, median would be 20_000 MXN/m2."""
    city = CityFactory(slug="tulum", name="Tulum")
    zone = ZoneFactory(slug="aldea-zama", name="Aldea Zama", city=city)
    PropertyTypeFactory(slug="casa", name="Casa")
    now = datetime.now(timezone.utc)

    # 5 USD comparables: $100k / 100m2 -> at rate 20.0 would yield 20_000 MXN/m2.
    for _ in range(5):
        ComparableFactory(
            city=city, zone=zone, currency="USD", price_usd=100000,
            area_m2=100, is_preventa=False, scraped_at=now,
        )

    result = await valuate(async_session, **REQUEST)

    # No rate row exists, so USDs must be DROPPED -- not converted at 20.0.
    assert result["price_per_m2_median_mxn"] != 20000
    assert result["price_per_m2_median_mxn"] is None
    assert result["comparables_count"] == 0
