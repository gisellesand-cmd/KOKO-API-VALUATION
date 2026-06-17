"""Pytest fixtures: in-memory aiosqlite engine + seed helpers."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models import Base, City, Comparable, PropertyType, Zone


@dataclass
class Taxonomy:
    city_id: uuid.UUID
    zone_id: uuid.UUID
    other_zone_id: uuid.UUID
    property_type_id: uuid.UUID


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncSession:
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session


@pytest_asyncio.fixture
async def taxonomy(db_session: AsyncSession) -> Taxonomy:
    city = City(id=uuid.uuid4(), name="Querétaro")
    zone = Zone(id=uuid.uuid4(), city_id=city.id, name="Centro")
    other_zone = Zone(id=uuid.uuid4(), city_id=city.id, name="Juriquilla")
    ptype = PropertyType(id=uuid.uuid4(), name="Casa")

    db_session.add_all([city, zone, other_zone, ptype])
    await db_session.commit()

    return Taxonomy(
        city_id=city.id,
        zone_id=zone.id,
        other_zone_id=other_zone.id,
        property_type_id=ptype.id,
    )


async def insert_comparable(
    session: AsyncSession,
    *,
    city_id: uuid.UUID,
    zone_id: Optional[uuid.UUID],
    property_type_id: uuid.UUID,
    operation: str = "venta",
    price_per_m2_mxn: float = 20000.0,
    currency: str = "MXN",
    is_preventa: bool = False,
    active: bool = True,
    scraped_at: Optional[datetime] = None,
) -> Comparable:
    if scraped_at is None:
        scraped_at = datetime.now(timezone.utc).replace(tzinfo=None)
    comp = Comparable(
        id=uuid.uuid4(),
        city_id=city_id,
        zone_id=zone_id,
        property_type_id=property_type_id,
        operation=operation,
        price_per_m2_mxn=price_per_m2_mxn,
        currency=currency,
        is_preventa=is_preventa,
        active=active,
        scraped_at=scraped_at,
    )
    session.add(comp)
    await session.commit()
    return comp


def make_kwargs(taxonomy: Taxonomy, **overrides: Any) -> dict:
    """Convenience: build insert_comparable kwargs with sensible defaults."""
    base = dict(
        city_id=taxonomy.city_id,
        zone_id=taxonomy.zone_id,
        property_type_id=taxonomy.property_type_id,
    )
    base.update(overrides)
    return base
