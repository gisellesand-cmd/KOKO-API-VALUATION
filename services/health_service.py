from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text

from db.models import City, Comparable, ScrapeLog
from db.session import session_scope
from services.config import get_settings
from services.logging import get_logger
from services.schemas import HealthCheckResult

_logger = get_logger(__name__)


async def check_health() -> HealthCheckResult:
    """Check DB connectivity, per-city comparable counts, and per-portal last successful scrape."""
    checked_at = datetime.now(timezone.utc)
    db_connected = False
    comparables_by_city: dict[str, int] = {}
    last_scrape_by_portal: dict[str, datetime | None] = {}

    try:
        async with session_scope() as session:
            ping = await session.execute(text("SELECT 1"))
            ping.scalar()
            db_connected = True

            settings = get_settings()
            cutoff = checked_at - timedelta(days=settings.comparable_freshness_days)

            counts_stmt = (
                select(City.slug, func.count(Comparable.id))
                .join(Comparable, Comparable.city_id == City.id)
                .where(Comparable.is_active.is_(True))
                .where(Comparable.scraped_at >= cutoff)
                .group_by(City.slug)
            )
            counts_res = await session.execute(counts_stmt)
            comparables_by_city = {slug: int(n) for slug, n in counts_res.all()}

            all_cities_stmt = select(City.slug)
            all_cities_res = await session.execute(all_cities_stmt)
            for (slug,) in all_cities_res.all():
                comparables_by_city.setdefault(slug, 0)

            portals_stmt = select(ScrapeLog.portal).distinct()
            portals_res = await session.execute(portals_stmt)
            portals = [row[0] for row in portals_res.all()]

            for portal in portals:
                last_stmt = (
                    select(func.max(ScrapeLog.finished_at))
                    .where(ScrapeLog.portal == portal)
                    .where(ScrapeLog.status == "success")
                )
                last_res = await session.execute(last_stmt)
                last_scrape_by_portal[portal] = last_res.scalar_one_or_none()
    except Exception as exc:
        _logger.error("health.db_error", error=str(exc))
        return HealthCheckResult(
            status="down",
            db_connected=False,
            comparables_by_city=comparables_by_city,
            last_scrape_by_portal=last_scrape_by_portal,
            checked_at=checked_at,
        )

    status = _derive_status(
        db_connected=db_connected,
        comparables_by_city=comparables_by_city,
        last_scrape_by_portal=last_scrape_by_portal,
        now=checked_at,
    )

    return HealthCheckResult(
        status=status,
        db_connected=db_connected,
        comparables_by_city=comparables_by_city,
        last_scrape_by_portal=last_scrape_by_portal,
        checked_at=checked_at,
    )


def _derive_status(
    *,
    db_connected: bool,
    comparables_by_city: dict[str, int],
    last_scrape_by_portal: dict[str, datetime | None],
    now: datetime,
) -> str:
    if not db_connected:
        return "down"
    degraded = False
    seven_days_ago = now - timedelta(days=7)
    for last in last_scrape_by_portal.values():
        if last is None or last < seven_days_ago:
            degraded = True
            break
    if not degraded:
        for count in comparables_by_city.values():
            if count == 0:
                degraded = True
                break
    return "degraded" if degraded else "ok"


__all__ = ["check_health"]
