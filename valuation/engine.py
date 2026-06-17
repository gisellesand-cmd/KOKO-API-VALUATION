from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Literal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Comparable
from services.config import get_settings


@dataclass(frozen=True)
class EngineRequest:
    city_id: int
    zone_id: int | None
    property_type_id: int
    operation: Literal["venta", "renta"]
    area_m2: float
    bedrooms: int | None
    bathrooms: int | None


@dataclass(frozen=True)
class EngineResult:
    confidence_level: Literal["alta", "media", "baja", "insuficiente"]
    comparables_count: int
    geographic_scope: Literal["zone", "city"]
    comparable_ids: list[int]
    price_min_mxn: float | None
    price_median_mxn: float | None
    price_max_mxn: float | None
    price_per_m2_median: float | None
    methodology_note: str


async def compute_valuation(session: AsyncSession, req: EngineRequest) -> EngineResult:
    """Stub engine: filters active, fresh comparables; widens zone to city when needed; returns price stats."""
    settings = get_settings()
    cutoff_days = settings.comparable_freshness_days

    geographic_scope: Literal["zone", "city"] = (
        "zone" if req.zone_id is not None else "city"
    )
    comps = await _fetch_comparables(
        session, req, use_zone=req.zone_id is not None, cutoff_days=cutoff_days
    )
    if (
        len(comps) < settings.min_comparables_low_confidence
        and req.zone_id is not None
    ):
        comps = await _fetch_comparables(
            session, req, use_zone=False, cutoff_days=cutoff_days
        )
        geographic_scope = "city"
    return _summarize(comps, geographic_scope, settings)


async def _fetch_comparables(
    session: AsyncSession,
    req: EngineRequest,
    *,
    use_zone: bool,
    cutoff_days: int,
) -> list[Comparable]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=cutoff_days)
    filters = [
        Comparable.city_id == req.city_id,
        Comparable.property_type_id == req.property_type_id,
        Comparable.operation == req.operation,
        Comparable.is_active.is_(True),
        Comparable.scraped_at >= cutoff,
    ]
    if use_zone and req.zone_id is not None:
        filters.append(Comparable.zone_id == req.zone_id)
    stmt = select(Comparable).where(and_(*filters))
    res = await session.execute(stmt)
    return list(res.scalars().all())


def _summarize(
    comps: list[Comparable],
    geographic_scope: Literal["zone", "city"],
    settings,
) -> EngineResult:
    n = len(comps)
    if n < settings.min_comparables_low_confidence:
        return EngineResult(
            confidence_level="insuficiente",
            comparables_count=n,
            geographic_scope=geographic_scope,
            comparable_ids=[c.id for c in comps],
            price_min_mxn=None,
            price_median_mxn=None,
            price_max_mxn=None,
            price_per_m2_median=None,
            methodology_note=(
                f"Solo se encontraron {n} comparables; se requieren al menos "
                f"{settings.min_comparables_low_confidence}."
            ),
        )

    prices = [c.price_mxn for c in comps]
    ppsm = [c.price_mxn / c.area_m2 for c in comps if c.area_m2 > 0]

    if n >= settings.min_comparables_high_confidence:
        conf: Literal["alta", "media", "baja", "insuficiente"] = "alta"
    elif n >= settings.min_comparables_medium_confidence:
        conf = "media"
    else:
        conf = "baja"

    return EngineResult(
        confidence_level=conf,
        comparables_count=n,
        geographic_scope=geographic_scope,
        comparable_ids=[c.id for c in comps],
        price_min_mxn=min(prices),
        price_median_mxn=median(prices),
        price_max_mxn=max(prices),
        price_per_m2_median=median(ppsm) if ppsm else None,
        methodology_note=(
            f"Mediana de {n} comparables ({geographic_scope}) en los últimos "
            f"{settings.comparable_freshness_days} días."
        ),
    )


__all__ = ["EngineRequest", "EngineResult", "compute_valuation"]
