from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional

from scrapers.base import ListingPayload

logger = logging.getLogger(__name__)

try:
    from sqlalchemy import select
    from db.models import City, ExchangeRate, PropertyType, Zone  # type: ignore
except ImportError:  # DB layer may not be present yet
    City = None  # type: ignore
    ExchangeRate = None  # type: ignore
    PropertyType = None  # type: ignore
    Zone = None  # type: ignore
    select = None  # type: ignore


async def _latest_usd_mxn_rate(session: Any, as_of_date) -> Optional[Decimal]:
    if ExchangeRate is None or select is None:
        logger.warning(
            "fx model unavailable",
            extra={"event": "fx_model_missing", "reason": "db_layer_not_imported"},
        )
        return None
    stmt = (
        select(ExchangeRate)
        .where(ExchangeRate.base_currency == "USD")
        .where(ExchangeRate.target_currency == "MXN")
        .where(ExchangeRate.valid_for_date <= as_of_date)
        .order_by(ExchangeRate.valid_for_date.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return Decimal(str(row.rate)) if row is not None else None


async def normalize_price_to_mxn(
    payload: ListingPayload, session: Any
) -> Optional[Decimal]:
    if payload.currency == "MXN":
        return payload.price
    if payload.currency == "USD":
        rate = await _latest_usd_mxn_rate(session, payload.scraped_at.date())
        if rate is None:
            logger.warning(
                "dropping USD listing — no FX rate available",
                extra={
                    "event": "fx_rate_missing",
                    "source_url": payload.source_url,
                    "scraped_at": payload.scraped_at.isoformat(),
                    "reason": "no_fx_rate_available",
                },
            )
            return None
        return payload.price * rate
    logger.warning(
        "unknown currency, dropping",
        extra={
            "event": "unknown_currency",
            "currency": payload.currency,
            "source_url": payload.source_url,
        },
    )
    return None


async def _resolve_city_id(session: Any, city_slug: str) -> Optional[int]:
    if City is None or select is None:
        return None
    stmt = select(City.id).where(City.slug == city_slug)
    return (await session.execute(stmt)).scalar_one_or_none()


async def _resolve_property_type_id(session: Any, pt_slug: str) -> Optional[int]:
    if PropertyType is None or select is None:
        return None
    stmt = select(PropertyType.id).where(PropertyType.slug == pt_slug)
    return (await session.execute(stmt)).scalar_one_or_none()


async def _resolve_zone_id(
    session: Any, city_id: int, zone_slug: Optional[str]
) -> Optional[int]:
    if not zone_slug or Zone is None or select is None:
        return None
    stmt = select(Zone.id).where(Zone.city_id == city_id).where(Zone.slug == zone_slug)
    return (await session.execute(stmt)).scalar_one_or_none()


async def normalize_payload(
    payload: ListingPayload, session: Any
) -> Optional[dict]:
    price_mxn = await normalize_price_to_mxn(payload, session)
    if price_mxn is None:
        return None
    if payload.price <= 0:
        logger.warning(
            "dropping non-positive price",
            extra={"event": "invalid_price", "source_url": payload.source_url},
        )
        return None
    # The Comparable table requires area_m2 (NOT NULL). The PRD rule
    # "no fabricated data" means we drop listings where the portal didn't
    # publish a square-meter figure rather than guess one.
    if not payload.area_m2 or payload.area_m2 <= 0:
        logger.info(
            "dropping listing — no area_m2",
            extra={"event": "missing_area", "source_url": payload.source_url},
        )
        return None
    if payload.area_m2 > 10_000_000:
        logger.info(
            "dropping listing — area_m2 implausibly large",
            extra={"event": "area_too_large", "area_m2": str(payload.area_m2), "source_url": payload.source_url},
        )
        return None
    city_id = await _resolve_city_id(session, payload.city)
    if city_id is None:
        logger.warning(
            "dropping listing — unknown city",
            extra={"event": "unknown_city", "city": payload.city, "source_url": payload.source_url},
        )
        return None
    property_type_id = await _resolve_property_type_id(session, payload.property_type)
    if property_type_id is None:
        logger.warning(
            "dropping listing — unknown property_type",
            extra={
                "event": "unknown_property_type",
                "property_type": payload.property_type,
                "source_url": payload.source_url,
            },
        )
        return None
    zone_id = await _resolve_zone_id(session, city_id, payload.zone)
    price_per_m2 = price_mxn / payload.area_m2
    return {
        "source": payload.source,
        "source_listing_id": payload.source_listing_id,
        "source_url": payload.source_url,
        "city_id": city_id,
        "zone_id": zone_id,
        "property_type_id": property_type_id,
        "operation": payload.operation,
        "price_original": payload.price,
        "currency_original": payload.currency,
        "price_mxn": price_mxn,
        "area_m2": payload.area_m2,
        "price_per_m2_mxn": price_per_m2,
        "bedrooms": payload.bedrooms,
        "bathrooms": payload.bathrooms,
        "address": payload.address,
        "title": payload.title,
        "is_preventa": payload.is_preventa,
        "scraped_at": payload.scraped_at,
        "last_seen_at": payload.scraped_at,
    }
