from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional

from scrapers.base import ListingPayload

logger = logging.getLogger(__name__)

try:
    from sqlalchemy import select
    from db.models import ExchangeRate  # type: ignore
except ImportError:  # DB layer may not be present yet
    ExchangeRate = None  # type: ignore
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
    price_per_m2 = None
    if payload.area_m2 and payload.area_m2 > 0:
        price_per_m2 = price_mxn / payload.area_m2
    return {
        "source": payload.source,
        "source_listing_id": payload.source_listing_id,
        "source_url": payload.source_url,
        "city": payload.city,
        "zone": payload.zone,
        "property_type": payload.property_type,
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
