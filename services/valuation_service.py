from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import City, PropertyType, ValuationRequest, ValuationResponse, Zone
from db.session import session_scope
from services.exceptions import (
    CityNotFoundError,
    PropertyTypeNotFoundError,
    ZoneNotFoundError,
)
from services.logging import bind_request_id, clear_request_context, get_logger
from services.schemas import DISCLAIMER_TEXT, ValuationInput, ValuationOutput
from valuation.engine import EngineRequest, compute_valuation

_logger = get_logger(__name__)


async def request_valuation(
    input: ValuationInput, session: AsyncSession | None = None
) -> ValuationOutput:
    """Resolve catalog slugs, run the engine, persist audit records, return ValuationOutput."""
    if session is None:
        async with session_scope() as owned_session:
            return await _request_valuation_inner(input, owned_session)
    return await _request_valuation_inner(input, session)


async def _request_valuation_inner(
    input: ValuationInput, session: AsyncSession
) -> ValuationOutput:
    request_id = uuid4()
    bind_request_id(request_id)
    try:
        _logger.info(
            "valuation.start",
            city_slug=input.city_slug,
            zone_slug=input.zone_slug,
            property_type_slug=input.property_type_slug,
            operation=input.operation,
        )

        city = await _resolve_city(session, input.city_slug)
        zone = await _resolve_zone(session, city.id, input.zone_slug)
        property_type = await _resolve_property_type(session, input.property_type_slug)

        engine_req = EngineRequest(
            city_id=city.id,
            zone_id=zone.id if zone else None,
            property_type_id=property_type.id,
            operation=input.operation,
            area_m2=input.area_m2,
            bedrooms=input.bedrooms,
            bathrooms=input.bathrooms,
        )
        result = await compute_valuation(session, engine_req)

        now = datetime.now(timezone.utc)
        req_row = ValuationRequest(
            id=request_id,
            city_id=city.id,
            zone_id=zone.id if zone else None,
            property_type_id=property_type.id,
            operation=input.operation,
            area_m2=input.area_m2,
            bedrooms=input.bedrooms,
            bathrooms=input.bathrooms,
            created_at=now,
        )
        resp_row = ValuationResponse(
            id=uuid4(),
            request_id=request_id,
            confidence_level=result.confidence_level,
            comparables_count=result.comparables_count,
            geographic_scope=result.geographic_scope,
            comparable_ids=list(result.comparable_ids),
            price_min_mxn=result.price_min_mxn,
            price_median_mxn=result.price_median_mxn,
            price_max_mxn=result.price_max_mxn,
            price_per_m2_median=result.price_per_m2_median,
            methodology_note=result.methodology_note,
            computed_at=now,
        )
        session.add(req_row)
        session.add(resp_row)
        await session.flush()

        _logger.info(
            "valuation.complete",
            comparables_count=result.comparables_count,
            confidence_level=result.confidence_level,
            geographic_scope=result.geographic_scope,
        )

        return ValuationOutput(
            request_id=request_id,
            confidence_level=result.confidence_level,
            comparables_count=result.comparables_count,
            geographic_scope=result.geographic_scope,
            price_min_mxn=result.price_min_mxn,
            price_median_mxn=result.price_median_mxn,
            price_max_mxn=result.price_max_mxn,
            price_per_m2_median=result.price_per_m2_median,
            methodology_note=result.methodology_note,
            computed_at=now,
            disclaimer=DISCLAIMER_TEXT,
        )
    finally:
        clear_request_context()


async def _resolve_city(session: AsyncSession, slug: str) -> City:
    stmt = select(City).where(City.slug == slug)
    res = await session.execute(stmt)
    city = res.scalar_one_or_none()
    if city is None:
        raise CityNotFoundError(
            f"City with slug '{slug}' not found", city_slug=slug
        )
    return city


async def _resolve_zone(
    session: AsyncSession, city_id: int, slug: str | None
) -> Zone | None:
    if slug is None:
        return None
    stmt = select(Zone).where(Zone.slug == slug, Zone.city_id == city_id)
    res = await session.execute(stmt)
    zone = res.scalar_one_or_none()
    if zone is None:
        raise ZoneNotFoundError(
            f"Zone with slug '{slug}' not found in city",
            zone_slug=slug,
            city_id=city_id,
        )
    return zone


async def _resolve_property_type(session: AsyncSession, slug: str) -> PropertyType:
    stmt = select(PropertyType).where(PropertyType.slug == slug)
    res = await session.execute(stmt)
    pt = res.scalar_one_or_none()
    if pt is None:
        raise PropertyTypeNotFoundError(
            f"Property type with slug '{slug}' not found", property_type_slug=slug
        )
    return pt


__all__ = ["request_valuation"]
