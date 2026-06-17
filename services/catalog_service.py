from __future__ import annotations

import asyncio
import time
from typing import Any

from sqlalchemy import select

from db.models import City, PropertyType, Zone
from db.session import session_scope
from services.config import get_settings
from services.exceptions import CityNotFoundError
from services.schemas import CityInfo, PropertyTypeInfo, ZoneInfo

_cache: dict[str, tuple[float, Any]] = {}
_lock = asyncio.Lock()


def _ttl() -> int:
    return get_settings().catalog_cache_ttl_seconds


def _get_cached(key: str) -> Any | None:
    entry = _cache.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if expires_at < time.monotonic():
        _cache.pop(key, None)
        return None
    return value


def _set_cached(key: str, value: Any) -> None:
    _cache[key] = (time.monotonic() + _ttl(), value)


async def list_cities() -> list[CityInfo]:
    """Return all cities (TTL-cached)."""
    key = "cities"
    cached = _get_cached(key)
    if cached is not None:
        return cached
    async with _lock:
        cached = _get_cached(key)
        if cached is not None:
            return cached
        async with session_scope() as session:
            stmt = select(City).order_by(City.name)
            res = await session.execute(stmt)
            cities = [
                CityInfo(slug=c.slug, name=c.name, state=c.state)
                for c in res.scalars().all()
            ]
        _set_cached(key, cities)
        return cities


async def list_zones(city_slug: str) -> list[ZoneInfo]:
    """Return zones for a city slug (TTL-cached). Raises CityNotFoundError if unknown."""
    key = f"zones:{city_slug}"
    cached = _get_cached(key)
    if cached is not None:
        return cached
    async with _lock:
        cached = _get_cached(key)
        if cached is not None:
            return cached
        async with session_scope() as session:
            city_stmt = select(City).where(City.slug == city_slug)
            city_res = await session.execute(city_stmt)
            city = city_res.scalar_one_or_none()
            if city is None:
                raise CityNotFoundError(
                    f"City with slug '{city_slug}' not found",
                    city_slug=city_slug,
                )
            zone_stmt = select(Zone).where(Zone.city_id == city.id).order_by(Zone.name)
            zone_res = await session.execute(zone_stmt)
            zones = [
                ZoneInfo(slug=z.slug, name=z.name, city_slug=city_slug)
                for z in zone_res.scalars().all()
            ]
        _set_cached(key, zones)
        return zones


async def list_property_types() -> list[PropertyTypeInfo]:
    """Return all property types (TTL-cached)."""
    key = "property_types"
    cached = _get_cached(key)
    if cached is not None:
        return cached
    async with _lock:
        cached = _get_cached(key)
        if cached is not None:
            return cached
        async with session_scope() as session:
            stmt = select(PropertyType).order_by(PropertyType.name)
            res = await session.execute(stmt)
            pts = [
                PropertyTypeInfo(slug=p.slug, name=p.name)
                for p in res.scalars().all()
            ]
        _set_cached(key, pts)
        return pts


def invalidate_catalog_cache() -> None:
    """Drop all cached catalog entries."""
    _cache.clear()


__all__ = [
    "list_cities",
    "list_zones",
    "list_property_types",
    "invalidate_catalog_cache",
]
