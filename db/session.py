from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services.config import get_settings

_engine = None
_sessionmaker = None


def _is_supabase(url: str) -> bool:
    return "supabase" in url


def get_engine():
    """Return the lazily-initialized async SQLAlchemy engine."""
    global _engine
    if _engine is None:
        db_url = get_settings().DATABASE_URL
        connect_args: dict = {}
        if _is_supabase(db_url):
            import ssl
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            connect_args["ssl"] = ssl_ctx
        if "pooler.supabase.com" in db_url:
            connect_args["statement_cache_size"] = 0
        _engine = create_async_engine(
            db_url,
            pool_pre_ping=True,
            future=True,
            connect_args=connect_args,
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the lazily-initialized async session factory."""
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _sessionmaker


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Async context manager yielding a session and committing on success."""
    sm = get_sessionmaker()
    async with sm() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


get_session = session_scope


__all__ = ["get_engine", "get_sessionmaker", "session_scope", "get_session"]
