"""
Enforces the confidence bucketing rule: 8+ valid in-zone comparables
MUST produce ``confidence == "alta"`` and the IQR invariant
``p25 <= median <= p75`` MUST hold.
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
@pytest.mark.parametrize("count", [8, 12, 20])
async def test_high_count_returns_alta(async_session, count):
    city = CityFactory(slug="tulum", name="Tulum")
    zone = ZoneFactory(slug="aldea-zama", name="Aldea Zama", city=city)
    PropertyTypeFactory(slug="casa", name="Casa")
    now = datetime.now(timezone.utc)

    # Linearly spaced clean prices.
    prices_per_m2 = [40000 + (i * 1000) for i in range(count)]
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

    assert result["confidence"] == "alta"
    assert result["comparables_count"] == count
    assert result["price_p25_mxn"] <= result["price_median_mxn"] <= result["price_p75_mxn"]
