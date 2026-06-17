"""
Enforces the preventa exclusion rule: comparables with ``is_preventa=True``
MUST ALWAYS be excluded. If only preventas exist, the result is insufficient
-- never a silently averaged number.
"""

# LOAD-BEARING: enforces "Cero datos inventados" -- do NOT skip or delete.

from __future__ import annotations

import statistics
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
async def test_preventas_are_excluded_from_median(async_session):
    city = CityFactory(slug="tulum", name="Tulum")
    zone = ZoneFactory(slug="aldea-zama", name="Aldea Zama", city=city)
    PropertyTypeFactory(slug="casa", name="Casa")
    now = datetime.now(timezone.utc)

    real_ppms = [44000, 45000, 46000, 47000, 48000, 49000]
    preventa_ppms = [10000, 12000, 14000, 80000, 90000, 100000]
    for ppm in real_ppms:
        ComparableFactory(
            city=city, zone=zone, currency="MXN", price_mxn=ppm * 200,
            area_m2=200, price_per_m2_mxn=ppm, is_preventa=False, scraped_at=now,
        )
    for ppm in preventa_ppms:
        ComparableFactory(
            city=city, zone=zone, currency="MXN", price_mxn=ppm * 200,
            area_m2=200, price_per_m2_mxn=ppm, is_preventa=True, scraped_at=now,
        )

    result = await valuate(async_session, **REQUEST)

    assert result["comparables_count"] == 6
    expected = statistics.median(real_ppms)
    assert result["price_per_m2_median_mxn"] == pytest.approx(expected, rel=0.01)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_only_preventas_yields_insufficient(async_session):
    city = CityFactory(slug="tulum", name="Tulum")
    zone = ZoneFactory(slug="aldea-zama", name="Aldea Zama", city=city)
    PropertyTypeFactory(slug="casa", name="Casa")
    now = datetime.now(timezone.utc)

    for ppm in [40000, 42000, 44000, 46000, 48000, 50000, 52000, 54000]:
        ComparableFactory(
            city=city, zone=zone, currency="MXN", price_mxn=ppm * 200,
            area_m2=200, price_per_m2_mxn=ppm, is_preventa=True, scraped_at=now,
        )

    result = await valuate(async_session, **REQUEST)

    assert result["comparables_count"] == 0
    assert result["confidence"] == "insuficiente"
    assert result["price_median_mxn"] is None
