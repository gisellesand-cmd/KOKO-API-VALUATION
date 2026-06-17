# Health tests rely on `patched_session_factory` to redirect
# db.session.get_sessionmaker / session_scope at the in-memory test engine,
# since health_service opens its own sessions internally.
from datetime import datetime, timezone, timedelta

from services import health_service


async def test_health_ok_when_db_and_comparables_present(
    session, seeded_catalog, seed_comparables, patched_session_factory
):
    from db.models import ScrapeLog

    await seed_comparables(5)
    log = ScrapeLog(
        portal="inmuebles24",
        status="ok",
        started_at=datetime.now(timezone.utc) - timedelta(hours=2),
        finished_at=datetime.now(timezone.utc) - timedelta(hours=1),
        items_scraped=5,
    )
    session.add(log)
    await session.commit()

    result = await health_service.check_health()

    assert result.status == "ok"
    assert result.db_connected is True
    assert "cdmx" in result.comparables_by_city
    assert "inmuebles24" in result.last_scrape_by_portal


async def test_health_degraded_when_no_recent_scrape(
    session, seeded_catalog, seed_comparables, patched_session_factory
):
    from db.models import ScrapeLog

    await seed_comparables(5)
    log = ScrapeLog(
        portal="inmuebles24",
        status="ok",
        started_at=datetime.now(timezone.utc) - timedelta(days=10),
        finished_at=datetime.now(timezone.utc) - timedelta(days=10),
        items_scraped=5,
    )
    session.add(log)
    await session.commit()

    result = await health_service.check_health()

    assert result.status == "degraded"
