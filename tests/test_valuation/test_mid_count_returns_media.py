"""
Enforces the confidence bucketing rule: 4-7 valid in-zone comparables
MUST produce ``confidence == "media"`` with a real, computed median.
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
@pytest.mark.parametrize("count", [4, 5, 6, 7])
async def test_mid_count_returns_media(async_session, count):
    city = CityFactory(slug="tulum", name="Tulum")
    zone = ZoneFactory(slug="aldea-zama", name="Aldea Zama", city=city)
    PropertyTypeFactory(slug="casa", name="Casa")
    now = datetime.now(timezone.utc)

    prices_per_m2 = [42000, 44000, 46000, 48000, 50000, 52000, 54000][:count]
    for ppm in prices_per_m2:
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

    result = await valuate(async_session, **REQUEST)

    assert result["confidence"] == "media"
    assert result["comparables_count"] == count
    expected_ppm = statistics.median(prices_per_m2)
    assert result["price_per_m2_median_mxn"] == pytest.approx(expected_ppm, rel=0.01)
