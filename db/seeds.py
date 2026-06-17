from __future__ import annotations

import logging
import unicodedata

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import City, Zone, PropertyType

logger = logging.getLogger(__name__)


def _slugify(name: str) -> str:
    norm = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(c for c in norm if not unicodedata.combining(c))
    return ascii_only.lower().strip().replace(" ", "-")


CITIES = [
    {"slug": "tulum", "name": "Tulum", "country": "MX", "state": "Quintana Roo"},
    {"slug": "cancun", "name": "Cancún", "country": "MX", "state": "Quintana Roo"},
    {"slug": "playa-del-carmen", "name": "Playa del Carmen", "country": "MX", "state": "Quintana Roo"},
]

ZONES_BY_CITY = {
    "tulum": ["Aldea Zama", "La Veleta", "Region 15", "Centro"],
    "cancun": ["Zona Hotelera", "Puerto Cancún", "Aqua", "Centro", "SM 17", "SM 21"],
    "playa-del-carmen": ["Playacar", "Centro", "Coco Beach", "Ejido"],
}

PROPERTY_TYPES = [
    {"slug": "casa", "name": "Casa"},
    {"slug": "departamento", "name": "Departamento"},
    {"slug": "terreno", "name": "Terreno"},
    {"slug": "local", "name": "Local Comercial"},
    {"slug": "villa", "name": "Villa"},
]


async def seed_all(session: AsyncSession) -> dict[str, int]:
    counts = {"cities": 0, "zones": 0, "property_types": 0}

    # CITIES — upsert idempotently
    for city_row in CITIES:
        stmt = pg_insert(City).values(**city_row)
        stmt = stmt.on_conflict_do_nothing(index_elements=["slug"])
        await session.execute(stmt)
    counts["cities"] = len(CITIES)

    # Fetch cities to get IDs for zone FK
    city_id_by_slug: dict[str, int] = {}
    res = await session.execute(select(City.id, City.slug))
    for cid, cslug in res.all():
        city_id_by_slug[cslug] = cid

    # ZONES — upsert idempotently per (city_id, slug)
    for city_slug, zone_names in ZONES_BY_CITY.items():
        cid = city_id_by_slug.get(city_slug)
        if cid is None:
            logger.warning(
                "seed: city not found for zone insert",
                extra={"city_slug": city_slug},
            )
            continue
        for zname in zone_names:
            zslug = _slugify(zname)
            stmt = pg_insert(Zone).values(
                city_id=cid, name=zname, slug=zslug
            )
            stmt = stmt.on_conflict_do_nothing(
                index_elements=["city_id", "slug"]
            )
            await session.execute(stmt)
            counts["zones"] += 1

    # PROPERTY TYPES — upsert idempotently
    for pt_row in PROPERTY_TYPES:
        stmt = pg_insert(PropertyType).values(**pt_row)
        stmt = stmt.on_conflict_do_nothing(index_elements=["slug"])
        await session.execute(stmt)
    counts["property_types"] = len(PROPERTY_TYPES)

    await session.flush()
    return counts


__all__ = ["seed_all", "CITIES", "ZONES_BY_CITY", "PROPERTY_TYPES"]
