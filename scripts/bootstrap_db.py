from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

# Ensure repo root on PYTHONPATH so `import db.models` resolves regardless of cwd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from db.models import Base, ExchangeRate
from db.seeds import seed_all


logger = logging.getLogger("bootstrap_db")


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    # Fallback: try services.config
    try:
        from services.config import get_settings

        return get_settings().DATABASE_URL
    except Exception:
        return "postgresql+asyncpg://gisellesandoval@localhost:5432/koko_valuation"


async def _fetch_banxico_rate(token: str) -> Decimal | None:
    url = (
        "https://www.banxico.org.mx/SieAPIRest/service/v1/series/"
        "SF43718/datos/oportuno"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers={"Bmx-Token": token})
            resp.raise_for_status()
            data = resp.json()
        dato = data["bmx"]["series"][0]["datos"][0]["dato"]
        return Decimal(str(dato).replace(",", ""))
    except Exception as exc:
        logger.warning("banxico fetch failed: %s", exc)
        return None


async def _ensure_fx_rate(session: AsyncSession) -> dict:
    today = date.today()
    # Has a USD/MXN rate for today already?
    res = await session.execute(
        select(ExchangeRate)
        .where(ExchangeRate.base_currency == "USD")
        .where(ExchangeRate.target_currency == "MXN")
        .where(ExchangeRate.valid_for_date == today)
        .limit(1)
    )
    if res.scalar_one_or_none() is not None:
        return {"fx_status": "exists"}

    token = os.environ.get("BANXICO_API_TOKEN")
    rate: Decimal | None = None
    source = "placeholder"
    if token:
        rate = await _fetch_banxico_rate(token)
        if rate is not None:
            source = "banxico"
    if rate is None:
        rate = Decimal("20.0")
        logger.warning(
            "inserting placeholder USD/MXN rate=20.0 (set BANXICO_API_TOKEN for real rate)"
        )

    stmt = pg_insert(ExchangeRate).values(
        base_currency="USD",
        target_currency="MXN",
        rate=rate,
        source=source,
        valid_for_date=today,
        fetched_at=datetime.now(timezone.utc),
    )
    stmt = stmt.on_conflict_do_nothing(
        constraint="uq_exchange_rate_pair_date_source"
    )
    await session.execute(stmt)
    return {"fx_status": source, "fx_rate": str(rate)}


async def main() -> int:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    url = _database_url()
    logger.info("connecting to %s", url.split("@")[-1])

    engine = create_async_engine(url, future=True)

    # 1. create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("tables created (or already present)")

    sessionmaker_ = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    async with sessionmaker_() as session:
        async with session.begin():
            counts = await seed_all(session)
            fx = await _ensure_fx_rate(session)

    table_count_q = (
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema = 'public'"
    )
    async with engine.connect() as conn:
        res = await conn.execute(text(table_count_q))
        n_tables = res.scalar_one()

    await engine.dispose()

    print(
        f"bootstrap done — tables_in_public={n_tables} cities={counts['cities']} "
        f"zones={counts['zones']} property_types={counts['property_types']} "
        f"fx_status={fx.get('fx_status')}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
