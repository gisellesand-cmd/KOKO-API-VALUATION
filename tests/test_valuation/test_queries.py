from datetime import datetime, timedelta, timezone

import pytest

from valuation.queries import fetch_comparables

from .conftest import insert_comparable, make_kwargs


@pytest.mark.asyncio
async def test_returns_only_matching_taxonomy(db_session, taxonomy):
    await insert_comparable(db_session, **make_kwargs(taxonomy, price_per_m2_mxn=20000.0))
    await insert_comparable(db_session, **make_kwargs(taxonomy, operation="renta"))

    results = await fetch_comparables(
        db_session,
        city_id=taxonomy.city_id,
        zone_id=taxonomy.zone_id,
        property_type_id=taxonomy.property_type_id,
        operation="venta",
    )
    assert len(results) == 1
    assert results[0].operation == "venta"


@pytest.mark.asyncio
async def test_excludes_preventa(db_session, taxonomy):
    await insert_comparable(db_session, **make_kwargs(taxonomy))
    await insert_comparable(db_session, **make_kwargs(taxonomy, is_preventa=True))

    results = await fetch_comparables(
        db_session,
        city_id=taxonomy.city_id,
        zone_id=taxonomy.zone_id,
        property_type_id=taxonomy.property_type_id,
        operation="venta",
    )
    assert len(results) == 1
    assert results[0].is_preventa is False


@pytest.mark.asyncio
async def test_excludes_inactive(db_session, taxonomy):
    await insert_comparable(db_session, **make_kwargs(taxonomy))
    await insert_comparable(db_session, **make_kwargs(taxonomy, active=False))

    results = await fetch_comparables(
        db_session,
        city_id=taxonomy.city_id,
        zone_id=taxonomy.zone_id,
        property_type_id=taxonomy.property_type_id,
        operation="venta",
    )
    assert len(results) == 1


@pytest.mark.asyncio
async def test_excludes_non_mxn(db_session, taxonomy):
    await insert_comparable(db_session, **make_kwargs(taxonomy))
    await insert_comparable(db_session, **make_kwargs(taxonomy, currency="USD"))

    results = await fetch_comparables(
        db_session,
        city_id=taxonomy.city_id,
        zone_id=taxonomy.zone_id,
        property_type_id=taxonomy.property_type_id,
        operation="venta",
    )
    assert len(results) == 1


@pytest.mark.asyncio
async def test_excludes_stale_rows(db_session, taxonomy):
    old = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=100)
    await insert_comparable(db_session, **make_kwargs(taxonomy))
    await insert_comparable(db_session, **make_kwargs(taxonomy, scraped_at=old))

    results = await fetch_comparables(
        db_session,
        city_id=taxonomy.city_id,
        zone_id=taxonomy.zone_id,
        property_type_id=taxonomy.property_type_id,
        operation="venta",
        days=90,
    )
    assert len(results) == 1


@pytest.mark.asyncio
async def test_zone_none_returns_city_wide(db_session, taxonomy):
    await insert_comparable(db_session, **make_kwargs(taxonomy))
    await insert_comparable(
        db_session,
        **make_kwargs(taxonomy, zone_id=taxonomy.other_zone_id),
    )

    zone_results = await fetch_comparables(
        db_session,
        city_id=taxonomy.city_id,
        zone_id=taxonomy.zone_id,
        property_type_id=taxonomy.property_type_id,
        operation="venta",
    )
    assert len(zone_results) == 1

    city_results = await fetch_comparables(
        db_session,
        city_id=taxonomy.city_id,
        zone_id=None,
        property_type_id=taxonomy.property_type_id,
        operation="venta",
    )
    assert len(city_results) == 2
