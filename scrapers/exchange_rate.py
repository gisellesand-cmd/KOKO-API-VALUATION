from __future__ import annotations

import argparse
import asyncio
import logging
import os
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

BANXICO_FIX_SERIES = "SF63528"
BANXICO_API_BASE = "https://www.banxico.org.mx/SieAPIRest/service/v1/series"

try:
    from sqlalchemy import select
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from db.models import ExchangeRate  # type: ignore
    from db.session import get_session  # type: ignore
except ImportError:  # DB layer may not be present yet
    ExchangeRate = None  # type: ignore
    select = None  # type: ignore
    pg_insert = None  # type: ignore
    get_session = None  # type: ignore


async def fetch_latest_fix_rate(
    token: str, client: Optional[httpx.AsyncClient] = None
) -> tuple[date, Decimal]:
    if not token:
        raise RuntimeError("BANXICO_API_TOKEN required")
    url = f"{BANXICO_API_BASE}/{BANXICO_FIX_SERIES}/datos/oportuno"
    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=30.0)
    try:
        resp = await client.get(url, headers={"Bmx-Token": token})
        resp.raise_for_status()
        payload = resp.json()
    finally:
        if owns_client:
            await client.aclose()

    try:
        datos = payload["bmx"]["series"][0]["datos"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"unexpected banxico response shape: {payload}") from exc
    if not datos:
        raise RuntimeError("banxico returned no observations")
    obs = datos[0]
    raw_date = obs.get("fecha")
    raw_value = obs.get("dato")
    if not raw_date or raw_value in (None, "", "N/E"):
        raise RuntimeError(f"banxico observation missing fields: {obs}")
    parsed_date = datetime.strptime(raw_date, "%d/%m/%Y").date()
    parsed_rate = Decimal(str(raw_value))
    return parsed_date, parsed_rate


async def upsert_rate_to_db(
    valid_for_date: date, rate: Decimal, session: Any
) -> None:
    if ExchangeRate is None or pg_insert is None:
        raise RuntimeError(
            "db.models.ExchangeRate not importable — DB layer must be built first"
        )
    row = {
        "currency_pair": "USD/MXN",
        "valid_for_date": valid_for_date,
        "rate": rate,
        "source": "banxico_fix",
    }
    stmt = pg_insert(ExchangeRate).values(**row)
    stmt = stmt.on_conflict_do_update(
        index_elements=["currency_pair", "valid_for_date"],
        set_={"rate": rate, "source": "banxico_fix"},
    )
    await session.execute(stmt)
    await session.commit()


async def run(token: Optional[str] = None) -> None:
    token = token or os.environ.get("BANXICO_API_TOKEN")
    if not token:
        raise RuntimeError(
            "BANXICO_API_TOKEN env var not set — register at "
            "https://www.banxico.org.mx/SieAPIRest"
        )
    valid_for_date, rate = await fetch_latest_fix_rate(token)
    logger.info(
        "fetched banxico FIX",
        extra={
            "event": "banxico_fetched",
            "valid_for_date": valid_for_date.isoformat(),
            "rate": str(rate),
        },
    )
    if get_session is None:
        logger.error(
            "db.session.get_session not importable — cannot persist rate",
            extra={"event": "db_unavailable"},
        )
        return
    async with get_session() as session:
        await upsert_rate_to_db(valid_for_date, rate, session)
    logger.info(
        "persisted FX rate",
        extra={
            "event": "banxico_persisted",
            "valid_for_date": valid_for_date.isoformat(),
            "rate": str(rate),
        },
    )


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch and persist Banxico FIX (USD/MXN).")
    p.add_argument("--token", help="Banxico API token (overrides BANXICO_API_TOKEN env)")
    return p.parse_args()


if __name__ == "__main__":
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    args = _parse_args()
    asyncio.run(run(args.token))
