"""
Enforces the IQR outlier filter: comparables whose ``price_per_m2_mxn``
falls outside ``[Q1 - 1.5*IQR, Q3 + 1.5*IQR]`` MUST be excluded before
the median is computed. Outliers must NOT pull the answer.
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

CLEAN_PRICES = [43000, 44000, 44500, 45000, 45000, 45500, 46000, 46000, 46500, 47000]


def _seed(city, zone, prices):
    now = datetime.now(timezone.utc)
    for ppm in prices:
        ComparableFactory(
            city=city,
            zone=zone,
            currency="MXN",
            price_mxn=ppm * 200,
            area_m2=200,
            price_per_m2_mxn=ppm,
            is_preventa=False,
            scraped_at=now,
        )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_iqr_removes_high_and_low_outliers(async_session):
    city = CityFactory(slug="tulum", name="Tulum")
    zone = ZoneFactory(slug="aldea-zama", name="Aldea Zama", city=city)
    PropertyTypeFactory(slug="casa", name="Casa")
    _seed(city, zone, CLEAN_PRICES + [200000, 5000])

    result = await valuate(async_session, **REQUEST)

    clean_median_ppm = statistics.median(CLEAN_PRICES)
    assert result["price_per_m2_median_mxn"] == pytest.approx(clean_median_ppm, rel=0.05)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_iqr_removes_low_outliers(async_session):
    city = CityFactory(slug="tulum", name="Tulum")
    zone = ZoneFactory(slug="aldea-zama", name="Aldea Zama", city=city)
    PropertyTypeFactory(slug="casa", name="Casa")
    _seed(city, zone, CLEAN_PRICES + [1000, 2000])

    result = await valuate(async_session, **REQUEST)

    clean_median_ppm = statistics.median(CLEAN_PRICES)
    assert result["price_per_m2_median_mxn"] == pytest.approx(clean_median_ppm, rel=0.05)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_iqr_keeps_borderline_values(async_session):
    city = CityFactory(slug="tulum", name="Tulum")
    zone = ZoneFactory(slug="aldea-zama", name="Aldea Zama", city=city)
    PropertyTypeFactory(slug="casa", name="Casa")
    # Borderline values within the natural spread should NOT be dropped.
    borderline = CLEAN_PRICES + [42000, 48000]
    _seed(city, zone, borderline)

    result = await valuate(async_session, **REQUEST)

    assert result["comparables_count"] == len(borderline)
