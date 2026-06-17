import os
import asyncio
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["ENVIRONMENT"] = "test"
os.environ["LOG_LEVEL"] = "WARNING"

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def engine():
    from db.models import Base
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture
async def session(session_factory):
    async with session_factory() as s:
        yield s


@pytest_asyncio.fixture
async def patched_session_factory(monkeypatch, session_factory):
    # Redirect db.session.get_sessionmaker/get_engine to use the test in-memory
    # engine so service-level code that opens its own session hits SQLite.
    import db.session as db_session

    monkeypatch.setattr(db_session, "get_sessionmaker", lambda: session_factory, raising=False)
    monkeypatch.setattr(
        db_session,
        "get_engine",
        lambda: session_factory.kw["bind"],
        raising=False,
    )

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _scope():
        async with session_factory() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    monkeypatch.setattr(db_session, "session_scope", _scope, raising=False)
    return session_factory


@pytest_asyncio.fixture
async def seeded_catalog(session):
    from db.models import City, Zone, PropertyType
    city = City(slug="cdmx", name="Ciudad de México", state="CDMX")
    session.add(city)
    await session.flush()
    zone = Zone(slug="roma", name="Roma Norte", city_id=city.id)
    session.add(zone)
    ptype = PropertyType(slug="departamento", name="Departamento")
    session.add(ptype)
    await session.commit()
    await session.refresh(city)
    await session.refresh(zone)
    await session.refresh(ptype)
    return {"city": city, "zone": zone, "property_type": ptype}


@pytest_asyncio.fixture
async def seed_comparables(session, seeded_catalog):
    from db.models import Comparable

    async def _seed(count: int, *, operation: str = "venta", base_price: float = 3_000_000.0,
                    base_area: float = 80.0, zone_match: bool = True):
        cat = seeded_catalog
        created = []
        for i in range(count):
            c = Comparable(
                portal="inmuebles24",
                external_id=f"ext-{i}-{uuid4().hex[:6]}",
                city_id=cat["city"].id,
                zone_id=cat["zone"].id if zone_match else None,
                property_type_id=cat["property_type"].id,
                operation=operation,
                price_mxn=base_price + i * 50_000,
                area_m2=base_area + (i % 5),
                bedrooms=2,
                bathrooms=2,
                is_active=True,
                scraped_at=datetime.now(timezone.utc) - timedelta(days=1 + (i % 5)),
            )
            session.add(c)
            created.append(c)
        await session.commit()
        return created

    return _seed
