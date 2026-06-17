"""Async DB queries for the valuation engine.

Filters are encapsulated here so that engine.py contains only business logic.
Only MXN-priced listings are returned: USD prices without a known FX rate would
violate the "cero datos inventados" policy.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Comparable


async def fetch_comparables(
    session: AsyncSession,
    *,
    city_id: int,
    zone_id: Optional[int],
    property_type_id: int,
    operation: str,
    days: int = 90,
) -> list[Comparable]:
    """Return active, non-preventa, MXN-priced Comparable rows matching the
    requested taxonomy and scraped within the last `days` days.

    When `zone_id` is None the query is city-wide (used by the engine's
    fallback path).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = select(Comparable).where(
        Comparable.city_id == city_id,
        Comparable.property_type_id == property_type_id,
        Comparable.operation == operation,
        Comparable.active.is_(True),
        Comparable.is_preventa.is_(False),
        Comparable.scraped_at >= cutoff,
    )
    if zone_id is not None:
        stmt = stmt.where(Comparable.zone_id == zone_id)

    result = await session.execute(stmt)
    return list(result.scalars().all())
