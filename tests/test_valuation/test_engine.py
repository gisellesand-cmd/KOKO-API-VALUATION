import pytest

from valuation.engine import ValuationEngine

from .conftest import insert_comparable, make_kwargs


@pytest.mark.asyncio
async def test_n_zero_returns_insuficiente(db_session, taxonomy):
    engine = ValuationEngine(db_session)
    result = await engine.compute(
        city_id=taxonomy.city_id,
        zone_id=taxonomy.zone_id,
        property_type_id=taxonomy.property_type_id,
        operation="venta",
        area_m2=100.0,
    )
    assert result.confidence_level == "insuficiente"
    assert result.comparables_count == 0
    assert result.geographic_scope is None
    assert result.price_min_mxn is None
    assert result.price_median_mxn is None
    assert result.price_max_mxn is None
    assert result.price_per_m2_median is None
    assert result.comparables_used_ids == []
    assert "90" in result.methodology_note


@pytest.mark.asyncio
async def test_n_one_returns_baja_at_zone(db_session, taxonomy):
    await insert_comparable(
        db_session,
        **make_kwargs(taxonomy, price_per_m2_mxn=25000.0),
    )
    engine = ValuationEngine(db_session)
    result = await engine.compute(
        city_id=taxonomy.city_id,
        zone_id=taxonomy.zone_id,
        property_type_id=taxonomy.property_type_id,
        operation="venta",
        area_m2=100.0,
    )
    # Zone has 1 row (<4) so it falls back to city. City also has 1 row, so
    # confidence "baja" stays "baja" even after downgrade, and scope=city.
    assert result.confidence_level == "baja"
    assert result.comparables_count == 1
    assert result.geographic_scope == "city"
    assert result.price_min_mxn == pytest.approx(2_500_000.0, rel=1e-3)
    assert result.price_median_mxn == pytest.approx(2_500_000.0, rel=1e-3)
    assert result.price_max_mxn == pytest.approx(2_500_000.0, rel=1e-3)
    assert result.price_per_m2_median == pytest.approx(25000.0, rel=1e-3)
    assert len(result.comparables_used_ids) == 1


@pytest.mark.asyncio
async def test_n_five_clean_returns_media_at_zone(db_session, taxonomy):
    for ppm2 in [20000.0, 21000.0, 22000.0, 23000.0, 24000.0]:
        await insert_comparable(
            db_session,
            **make_kwargs(taxonomy, price_per_m2_mxn=ppm2),
        )
    engine = ValuationEngine(db_session)
    result = await engine.compute(
        city_id=taxonomy.city_id,
        zone_id=taxonomy.zone_id,
        property_type_id=taxonomy.property_type_id,
        operation="venta",
        area_m2=80.0,
    )
    assert result.confidence_level == "media"
    assert result.comparables_count == 5
    assert result.geographic_scope == "zone"
    assert result.price_median_mxn == pytest.approx(22000.0 * 80, rel=1e-3)
    assert "zona" in result.methodology_note.lower()


@pytest.mark.asyncio
async def test_n_ten_with_outlier_removed(db_session, taxonomy):
    for _ in range(9):
        await insert_comparable(
            db_session,
            **make_kwargs(taxonomy, price_per_m2_mxn=20000.0),
        )
    await insert_comparable(
        db_session,
        **make_kwargs(taxonomy, price_per_m2_mxn=100000.0),
    )
    engine = ValuationEngine(db_session)
    result = await engine.compute(
        city_id=taxonomy.city_id,
        zone_id=taxonomy.zone_id,
        property_type_id=taxonomy.property_type_id,
        operation="venta",
        area_m2=100.0,
    )
    # Outlier removed, N=9 survivors -> "alta" (>=8) at zone scope.
    assert result.comparables_count == 9
    assert result.confidence_level == "alta"
    assert result.geographic_scope == "zone"
    assert result.price_median_mxn == pytest.approx(20000.0 * 100, rel=1e-3)
    assert "atípico" in result.methodology_note


@pytest.mark.asyncio
async def test_fallback_to_city_downgrades_confidence(db_session, taxonomy):
    # Target zone has only 2 rows -> triggers fallback.
    for _ in range(2):
        await insert_comparable(
            db_session,
            **make_kwargs(taxonomy, price_per_m2_mxn=22000.0),
        )
    # Other zone in same city contributes 5 more -> city-wide total = 7.
    for _ in range(5):
        await insert_comparable(
            db_session,
            **make_kwargs(
                taxonomy,
                zone_id=taxonomy.other_zone_id,
                price_per_m2_mxn=23000.0,
            ),
        )

    engine = ValuationEngine(db_session)
    result = await engine.compute(
        city_id=taxonomy.city_id,
        zone_id=taxonomy.zone_id,
        property_type_id=taxonomy.property_type_id,
        operation="venta",
        area_m2=50.0,
    )
    # N=7 city-wide -> base "media" -> downgrade to "baja" because of fallback.
    assert result.comparables_count == 7
    assert result.geographic_scope == "city"
    assert result.confidence_level == "baja"
    assert "ciudad" in result.methodology_note.lower()


@pytest.mark.asyncio
async def test_preventas_excluded(db_session, taxonomy):
    for _ in range(5):
        await insert_comparable(
            db_session,
            **make_kwargs(taxonomy, price_per_m2_mxn=20000.0),
        )
    for _ in range(3):
        await insert_comparable(
            db_session,
            **make_kwargs(taxonomy, price_per_m2_mxn=99999.0, is_preventa=True),
        )

    engine = ValuationEngine(db_session)
    result = await engine.compute(
        city_id=taxonomy.city_id,
        zone_id=taxonomy.zone_id,
        property_type_id=taxonomy.property_type_id,
        operation="venta",
        area_m2=100.0,
    )
    assert result.comparables_count == 5
    assert result.price_median_mxn == pytest.approx(20000.0 * 100, rel=1e-3)


@pytest.mark.asyncio
async def test_comparables_used_ids_returned(db_session, taxonomy):
    inserted_ids = []
    for ppm2 in [20000.0, 21000.0, 22000.0, 23000.0, 24000.0]:
        comp = await insert_comparable(
            db_session,
            **make_kwargs(taxonomy, price_per_m2_mxn=ppm2),
        )
        inserted_ids.append(comp.id)

    engine = ValuationEngine(db_session)
    result = await engine.compute(
        city_id=taxonomy.city_id,
        zone_id=taxonomy.zone_id,
        property_type_id=taxonomy.property_type_id,
        operation="venta",
        area_m2=80.0,
    )
    assert len(result.comparables_used_ids) == 5
    assert set(result.comparables_used_ids) == set(inserted_ids)
