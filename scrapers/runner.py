from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from scrapers.apify_runner import ApifyScraper, ConfigurationError
from scrapers.base import ScrapeError
from scrapers.inmuebles24 import Inmuebles24Scraper
from scrapers.normalize import normalize_payload
from scrapers.vivanuncios import VivanunciosScraper

logger = logging.getLogger(__name__)

try:
    from sqlalchemy import literal_column, select
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from db.models import Comparable, ScrapeRun  # type: ignore
    from db.session import get_session  # type: ignore
except ImportError:
    Comparable = None  # type: ignore
    ScrapeRun = None  # type: ignore
    literal_column = None  # type: ignore
    select = None  # type: ignore
    pg_insert = None  # type: ignore
    get_session = None  # type: ignore


SCRAPERS = {
    "inmuebles24": Inmuebles24Scraper,
    "vivanuncios": VivanunciosScraper,
}


def _resolve_via(requested: str) -> str:
    if requested == "auto":
        return "apify" if os.environ.get("APIFY_TOKEN") else "httpx"
    return requested


def _build_scraper(source: str, via: str):
    if via == "apify":
        return ApifyScraper(source_key=source)
    cls = SCRAPERS.get(source)
    if cls is None:
        raise RuntimeError(f"unknown source: {source}")
    return cls()


async def _upsert_comparable(session: Any, data: dict) -> str:
    if Comparable is None or pg_insert is None:
        raise RuntimeError(
            "db.models.Comparable not importable — DB layer must be built first"
        )
    update_cols = {
        "price_original": data["price_original"],
        "currency_original": data["currency_original"],
        "price_mxn": data["price_mxn"],
        "area_m2": data["area_m2"],
        "price_per_m2_mxn": data["price_per_m2_mxn"],
        "bedrooms": data["bedrooms"],
        "bathrooms": data["bathrooms"],
        "address": data["address"],
        "title": data["title"],
        "is_preventa": data["is_preventa"],
        "last_seen_at": data["last_seen_at"],
    }
    stmt = pg_insert(Comparable).values(**data)
    stmt = stmt.on_conflict_do_update(
        index_elements=["source", "source_listing_id"],
        set_=update_cols,
    )
    # xmax = 0 on the inserted row → freshly inserted; non-zero → updated.
    # xmax is a Postgres system column not in the ORM mapping, so use literal_column.
    stmt = stmt.returning((literal_column("xmax") == 0).label("inserted"))
    result = await session.execute(stmt)
    row = result.first()
    if row is not None and getattr(row, "inserted", False):
        return "inserted"
    return "updated"


async def _create_scrape_run(
    session: Any,
    source: str,
    city: str,
    zone: Optional[str],
    property_type: str,
    operation: str,
    max_pages: int,
) -> Any:
    if ScrapeRun is None:
        raise RuntimeError(
            "db.models.ScrapeRun not importable — DB layer must be built first"
        )
    row = ScrapeRun(
        source=source,
        city=city,
        zone=zone,
        property_type=property_type,
        operation=operation,
        max_pages=max_pages,
        started_at=datetime.now(timezone.utc),
        status="running",
    )
    session.add(row)
    await session.flush()
    return row


async def _finalize_scrape_run(
    session: Any,
    run_row: Any,
    *,
    status: str,
    error_message: Optional[str],
    scraped: int,
    inserted: int,
    updated: int,
    dropped: int,
) -> None:
    run_row.finished_at = datetime.now(timezone.utc)
    run_row.status = status
    run_row.error_message = error_message
    run_row.listings_scraped = scraped
    run_row.listings_inserted = inserted
    run_row.listings_updated = updated
    run_row.listings_dropped = dropped
    await session.commit()


async def main() -> int:
    args = _parse_args()
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    if args.source not in SCRAPERS:
        logger.error("unknown source", extra={"source": args.source})
        return 1

    via = _resolve_via(args.via)
    logger.info(
        "selected scrape backend",
        extra={"event": "via_selected", "via": via, "requested": args.via},
    )

    try:
        scraper = _build_scraper(args.source, via)
    except ConfigurationError as exc:
        logger.error(
            "scraper configuration failed",
            extra={"event": "scraper_config_failed", "via": via, "error": str(exc)},
        )
        return 1

    run_row = None
    session_ctx = None
    session = None
    if not args.dry_run:
        if get_session is None:
            logger.error(
                "db.session.get_session not importable — cannot persist; use --dry-run",
                extra={"event": "db_unavailable"},
            )
            return 1
        session_ctx = get_session()
        session = await session_ctx.__aenter__()
        run_row = await _create_scrape_run(
            session,
            args.source,
            args.city,
            args.zone,
            args.property_type,
            args.operation,
            args.pages,
        )

    scraped = inserted = updated = dropped = 0
    status = "completed"
    error_message: Optional[str] = None

    try:
        async with scraper:
            payloads = await scraper.scrape(
                args.city,
                args.zone,
                args.property_type,
                args.operation,
                args.pages,
            )
        scraped = len(payloads)
        if args.dry_run:
            logger.info(
                "dry-run skipping DB writes",
                extra={"event": "dry_run", "scraped": scraped},
            )
        else:
            for payload in payloads:
                normalized = await normalize_payload(payload, session)
                if normalized is None:
                    dropped += 1
                    continue
                outcome = await _upsert_comparable(session, normalized)
                if outcome == "inserted":
                    inserted += 1
                else:
                    updated += 1
            await session.commit()
    except ScrapeError as exc:
        status = "failed"
        error_message = str(exc)
        logger.error(
            "scrape failed",
            extra={
                "event": "scrape_failed",
                "source": args.source,
                "error": error_message,
            },
        )
    except Exception as exc:
        status = "failed"
        error_message = f"unexpected:{type(exc).__name__}:{exc}"
        logger.exception(
            "scrape crashed",
            extra={"event": "scrape_crashed", "source": args.source},
        )
    finally:
        if run_row is not None and session is not None:
            try:
                await _finalize_scrape_run(
                    session,
                    run_row,
                    status=status,
                    error_message=error_message,
                    scraped=scraped,
                    inserted=inserted,
                    updated=updated,
                    dropped=dropped,
                )
            except Exception:
                logger.exception(
                    "failed to finalize scrape_run row",
                    extra={"event": "scrape_run_finalize_failed"},
                )
        if session_ctx is not None:
            await session_ctx.__aexit__(None, None, None)

    zone_str = args.zone or "-"
    print(
        f"{args.source} {args.city}/{zone_str} "
        f"{args.property_type}/{args.operation}: "
        f"scraped={scraped} inserted={inserted} updated={updated} "
        f"dropped={dropped} status={status}"
    )
    return 0 if status == "completed" else 1


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run a single portal scrape.")
    p.add_argument("--source", required=True, choices=list(SCRAPERS.keys()))
    p.add_argument("--city", required=True)
    p.add_argument("--zone", default=None)
    p.add_argument(
        "--property-type",
        dest="property_type",
        default="casa",
        choices=["casa", "departamento", "terreno", "local", "oficina"],
    )
    p.add_argument(
        "--operation", default="venta", choices=["venta", "renta"]
    )
    p.add_argument("--pages", type=int, default=5)
    p.add_argument("--dry-run", dest="dry_run", action="store_true")
    p.add_argument(
        "--via",
        default="auto",
        choices=["auto", "apify", "httpx"],
        help="Scrape backend. 'auto' = apify if APIFY_TOKEN set, else httpx.",
    )
    return p.parse_args()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
