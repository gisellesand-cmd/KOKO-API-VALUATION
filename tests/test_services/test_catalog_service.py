# Catalog tests rely on `patched_session_factory` to redirect
# db.session.get_sessionmaker / session_scope at the in-memory test engine,
# since catalog_service opens its own sessions internally.
import pytest

from services.exceptions import CityNotFoundError
from services import catalog_service


async def test_list_cities_returns_seeded(seeded_catalog, patched_session_factory):
    catalog_service.invalidate_catalog_cache()
    cities = await catalog_service.list_cities()
    slugs = {c.slug for c in cities}
    assert "cdmx" in slugs


async def test_list_zones_unknown_city_raises_CityNotFoundError(
    seeded_catalog, patched_session_factory
):
    catalog_service.invalidate_catalog_cache()
    with pytest.raises(CityNotFoundError):
        await catalog_service.list_zones("ciudad-fantasma")


async def test_list_zones_returns_seeded(seeded_catalog, patched_session_factory):
    catalog_service.invalidate_catalog_cache()
    zones = await catalog_service.list_zones("cdmx")
    slugs = {z.slug for z in zones}
    assert "roma" in slugs


async def test_list_property_types_returns_seeded(
    seeded_catalog, patched_session_factory
):
    catalog_service.invalidate_catalog_cache()
    ptypes = await catalog_service.list_property_types()
    slugs = {p.slug for p in ptypes}
    assert "departamento" in slugs


async def test_catalog_cache_is_invalidated(
    seeded_catalog, patched_session_factory, session
):
    from db.models import City

    catalog_service.invalidate_catalog_cache()
    first = await catalog_service.list_cities()
    assert any(c.slug == "cdmx" for c in first)

    extra = City(slug="gdl", name="Guadalajara", state="JAL")
    session.add(extra)
    await session.commit()

    cached = await catalog_service.list_cities()
    cached_slugs = {c.slug for c in cached}

    catalog_service.invalidate_catalog_cache()
    refreshed = await catalog_service.list_cities()
    refreshed_slugs = {c.slug for c in refreshed}

    # After invalidation the new city should appear (it may or may not in the
    # cached read above depending on TTL behaviour, but post-invalidation it must).
    assert "gdl" in refreshed_slugs
    assert "cdmx" in cached_slugs
