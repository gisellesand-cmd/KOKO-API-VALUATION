"""
Global pytest fixtures for the KOKO MLS Property Valuation API test suite.

This module wires together:
  * an ephemeral Postgres instance (via testcontainers) for integration tests
  * an async SQLAlchemy session, transaction-rolled-back per test
  * an httpx.AsyncClient bound to the FastAPI app via ASGI transport
  * auth headers helper for API-key protected routes
  * factory-boy session binding (autouse) so factories "just work" in tests
"""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Generator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer

# Application imports. We assume the standard layout described in the PRD:
#   - FastAPI app instance lives at `app.main:app`
#   - SQLAlchemy declarative Base lives at `app.db.session:Base`
# These are imported lazily inside fixtures where appropriate to avoid
# blowing up collection when the dependencies are not yet installed.


# ---------------------------------------------------------------------------
# Event loop
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Session-scoped event loop so async fixtures can share state."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Postgres container
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    """
    Spin up a real Postgres for the whole test session.

    Using a real Postgres (not SQLite) is intentional: the valuation core
    relies on PG-specific features (NUMERIC precision, percentile aggregates,
    JSONB, etc.) and we will not pretend otherwise in tests.
    """
    with PostgresContainer("postgres:16-alpine") as container:
        yield container


@pytest_asyncio.fixture(scope="session")
async def _async_engine(postgres_container: PostgresContainer):
    """Build an async engine pointed at the testcontainer."""
    # testcontainers gives us a sync URL like "postgresql+psycopg2://..."; we
    # rewrite it for asyncpg.
    raw_url = postgres_container.get_connection_url()
    async_url = raw_url.replace("postgresql+psycopg2", "postgresql+asyncpg")
    if "+asyncpg" not in async_url:
        async_url = async_url.replace("postgresql://", "postgresql+asyncpg://")

    engine = create_async_engine(async_url, future=True, echo=False)

    # Create schema once for the session. We import Base lazily so collection
    # does not explode if the app package is missing during scaffolding.
    from app.db.session import Base  # type: ignore

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


# ---------------------------------------------------------------------------
# Async session (transaction-per-test, rolled back)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def async_session(_async_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a transactional AsyncSession.

    Each test runs inside a transaction that is rolled back at teardown,
    keeping tests isolated without paying the cost of re-creating the
    schema between tests.
    """
    connection = await _async_engine.connect()
    transaction = await connection.begin()

    session_factory = async_sessionmaker(
        bind=connection,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    session = session_factory()

    try:
        yield session
    finally:
        await session.close()
        if transaction.is_active:
            await transaction.rollback()
        await connection.close()


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def api_client(async_session: AsyncSession) -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    httpx.AsyncClient that talks to the FastAPI app in-process via ASGI.

    The DB dependency is overridden to hand out our transactional session
    so that anything the API writes is rolled back at the end of the test.
    """
    from app.main import app  # type: ignore

    # Best-effort dependency override. We try common dep names; if none are
    # defined in app.db.session, the override simply has no effect.
    try:
        from app.db.session import get_session  # type: ignore

        async def _override_get_session() -> AsyncGenerator[AsyncSession, None]:
            yield async_session

        app.dependency_overrides[get_session] = _override_get_session
    except ImportError:  # pragma: no cover - depends on app layout
        pass

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def auth_headers() -> dict[str, str]:
    """Headers carrying a valid free-tier API key for protected routes."""
    return {"X-API-Key": "test-key-free"}


@pytest.fixture(scope="function")
def auth_headers_paid() -> dict[str, str]:
    """Headers carrying a valid paid-tier API key for higher-quota tests."""
    return {"X-API-Key": "test-key-paid"}


# ---------------------------------------------------------------------------
# Factory wiring
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _wire_factories(async_session: AsyncSession) -> None:
    """
    Autouse fixture that points every factory-boy SQLAlchemyModelFactory at
    the per-test session, so tests can simply call `CityFactory()` without
    having to pass a session in.

    factory-boy expects a sync Session for `sqlalchemy_session`. We hand it
    the *sync* shadow of the async session by exposing the underlying
    connection's sync_session attribute when available; otherwise we attach
    the async session itself and rely on factory subclasses to await.
    """
    from tests import factories  # noqa: WPS433 - local import is intentional

    sync_session_proxy = getattr(async_session, "sync_session", async_session)

    for factory_cls in factories.ALL_FACTORIES:
        factory_cls._meta.sqlalchemy_session = sync_session_proxy  # type: ignore[attr-defined]
