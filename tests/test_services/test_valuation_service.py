import pytest
from sqlalchemy import select

from services.schemas import ValuationInput, DISCLAIMER_TEXT
from services.exceptions import (
    CityNotFoundError,
    ZoneNotFoundError,
    PropertyTypeNotFoundError,
)
from services.valuation_service import request_valuation


async def test_returns_alta_confidence_with_30_plus_comparables(
    session, seeded_catalog, seed_comparables
):
    await seed_comparables(30)
    payload = ValuationInput(
        city_slug="cdmx",
        zone_slug="roma",
        property_type_slug="departamento",
        operation="venta",
        area_m2=80,
    )

    result = await request_valuation(payload, session=session)

    assert result.confidence_level == "alta"
    assert result.comparables_count == 30
    assert result.geographic_scope == "zone"
    assert result.price_median_mxn is not None
    assert result.disclaimer == DISCLAIMER_TEXT


async def test_insufficient_data_returns_none_prices(
    session, seeded_catalog, seed_comparables
):
    await seed_comparables(2)
    payload = ValuationInput(
        city_slug="cdmx",
        zone_slug="roma",
        property_type_slug="departamento",
        operation="venta",
        area_m2=80,
    )

    result = await request_valuation(payload, session=session)

    assert result.confidence_level == "insuficiente"
    assert result.price_median_mxn is None
    assert result.price_min_mxn is None


async def test_unknown_city_raises_CityNotFoundError(session):
    payload = ValuationInput(
        city_slug="ciudad-inexistente",
        property_type_slug="departamento",
        operation="venta",
        area_m2=80,
    )

    with pytest.raises(CityNotFoundError):
        await request_valuation(payload, session=session)


async def test_unknown_zone_raises_ZoneNotFoundError(session, seeded_catalog):
    payload = ValuationInput(
        city_slug="cdmx",
        zone_slug="polanco",
        property_type_slug="departamento",
        operation="venta",
        area_m2=80,
    )

    with pytest.raises(ZoneNotFoundError):
        await request_valuation(payload, session=session)


async def test_unknown_property_type_raises_PropertyTypeNotFoundError(
    session, seeded_catalog
):
    payload = ValuationInput(
        city_slug="cdmx",
        property_type_slug="castillo",
        operation="venta",
        area_m2=80,
    )

    with pytest.raises(PropertyTypeNotFoundError):
        await request_valuation(payload, session=session)


async def test_widens_to_city_when_zone_has_few_comparables(
    session, seeded_catalog, seed_comparables
):
    await seed_comparables(10, zone_match=False)
    await seed_comparables(2, zone_match=True)

    payload = ValuationInput(
        city_slug="cdmx",
        zone_slug="roma",
        property_type_slug="departamento",
        operation="venta",
        area_m2=80,
    )

    result = await request_valuation(payload, session=session)

    assert result.geographic_scope == "city"
    assert result.comparables_count >= 10


async def test_persists_request_and_response_with_comparable_ids(
    session, seeded_catalog, seed_comparables
):
    from db.models import ValuationRequest, ValuationResponse

    await seed_comparables(10)
    payload = ValuationInput(
        city_slug="cdmx",
        zone_slug="roma",
        property_type_slug="departamento",
        operation="venta",
        area_m2=80,
    )

    result = await request_valuation(payload, session=session)

    requests = (await session.execute(select(ValuationRequest))).scalars().all()
    responses = (await session.execute(select(ValuationResponse))).scalars().all()

    assert len(requests) == 1
    assert len(responses) == 1

    response = responses[0]
    request = requests[0]

    assert isinstance(response.comparable_ids, list)
    assert len(response.comparable_ids) == result.comparables_count
    assert response.request_id == request.id
