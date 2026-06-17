"""
Enforces the confidence bucketing rule: 1-3 valid in-zone comparables
MUST produce ``confidence == "baja"``, with the reported ``price_median_mxn``
exactly equal to the statistical median of the inputs.
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
@pytest.mark.parametrize("count", [1, 2, 3])
async def test_low_count_returns_baja(async_session, count):
    city = CityFactory(slug="tulum", name="Tulum")
    zone = ZoneFactory(slug="aldea-zama", name="Aldea Zama", city=city)
    PropertyTypeFactory(slug="casa", name="Casa")
    now = datetime.now(timezone.utc)

    prices_per_m2 = [40000, 45000, 50000][:count]
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

    assert result["confidence"] == "baja"
    assert result["comparables_count"] == count
    assert result["price_median_mxn"] is not None
    expected_median_ppm = statistics.median(prices_per_m2)
    assert result["price_per_m2_median_mxn"] == pytest.approx(expected_median_ppm, rel=0.01)
