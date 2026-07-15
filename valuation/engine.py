"""ValuationEngine — the public orchestrator.

Pipeline: query comparables -> fallback to city if zone is sparse ->
IQR outlier filter -> percentile-based range -> classify confidence ->
ValuationResult with auditable comparable ids.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from .confidence import classify_confidence
from .outliers import filter_iqr
from .queries import fetch_comparables
from .result import ValuationResult

_LOOKBACK_DAYS = 90
_ZONE_MIN_FOR_NO_FALLBACK = 4


def _align_survivors(comparables, raw_values, kept_values):
    """Match each kept value back to a comparable row by index.
    Preserves duplicate handling: if two rows share the same price and that
    price survives the filter, both rows survive.
    """
    remaining = list(kept_values)
    survivors = []
    for comp, value in zip(comparables, raw_values):
        for i, kv in enumerate(remaining):
            if value == kv:
                remaining.pop(i)
                survivors.append(comp)
                break
    return survivors


class ValuationEngine:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def compute(
        self,
        *,
        city_id: UUID,
        zone_id: Optional[UUID],
        property_type_id: UUID,
        operation: str,
        area_m2: float,
    ) -> ValuationResult:
        comparables = await fetch_comparables(
            self.session,
            city_id=city_id,
            zone_id=zone_id,
            property_type_id=property_type_id,
            operation=operation,
            days=_LOOKBACK_DAYS,
        )

        fallback_to_city = False
        fallback_to_general = False
        geographic_scope: Optional[str] = "zone" if zone_id is not None else "city"

        if zone_id is not None and len(comparables) < _ZONE_MIN_FOR_NO_FALLBACK:
            city_wide = await fetch_comparables(
                self.session,
                city_id=city_id,
                zone_id=None,
                property_type_id=property_type_id,
                operation=operation,
                days=_LOOKBACK_DAYS,
            )
            comparables = city_wide
            fallback_to_city = True
            geographic_scope = "city"

        if not comparables:
            general_market = await fetch_comparables(
                self.session,
                city_id=city_id,
                zone_id=None,
                property_type_id=None,
                operation=operation,
                days=_LOOKBACK_DAYS,
            )
            if general_market:
                comparables = general_market
                fallback_to_general = True
                fallback_to_city = True
                geographic_scope = "city"

        if not comparables:
            return ValuationResult(
                confidence_level="insuficiente",
                comparables_count=0,
                geographic_scope=None,
                price_min_mxn=None,
                price_median_mxn=None,
                price_max_mxn=None,
                price_per_m2_median=None,
                comparables_used_ids=[],
                methodology_note=(
                    "Sin anuncios comparables recientes en los últimos "
                    f"{_LOOKBACK_DAYS} días. No es posible estimar un rango "
                    "de valor con datos reales."
                ),
            )

        raw_values = [float(c.price_per_m2_mxn) for c in comparables]
        kept_values = filter_iqr(raw_values)
        survivors = _align_survivors(comparables, raw_values, kept_values)
        n_after = len(survivors)
        n_outliers = len(comparables) - n_after

        arr = np.asarray([c.price_per_m2_mxn for c in survivors], dtype=float)
        p25, median_ppm2, p75 = np.percentile(arr, [25, 50, 75], method="linear")

        price_min_mxn = round(float(p25) * area_m2, 2)
        price_median_mxn = round(float(median_ppm2) * area_m2, 2)
        price_max_mxn = round(float(p75) * area_m2, 2)

        confidence_level = classify_confidence(n_after, fallback_to_city)
        if fallback_to_general:
            confidence_level = "baja"

        scope_label = "la zona solicitada" if geographic_scope == "zone" else "la ciudad"
        note = (
            f"Rango basado en {n_after} anuncio(s) reales de {scope_label} "
            f"en los últimos {_LOOKBACK_DAYS} días."
        )
        if n_outliers:
            note += f" Se descartaron {n_outliers} valor(es) atípico(s) por IQR."
        if fallback_to_general:
            note += (
                " No se encontraron anuncios del tipo de propiedad solicitado. "
                "Esta estimación se basa en el precio por m² del mercado "
                "general de la ciudad. Úsala como referencia aproximada."
            )
        elif fallback_to_city:
            note += (
                " La zona específica no alcanzó el mínimo de 4 anuncios, "
                "por lo que la búsqueda se amplió a toda la ciudad y la "
                "confianza se redujo un nivel."
            )

        return ValuationResult(
            confidence_level=confidence_level,
            comparables_count=n_after,
            geographic_scope=geographic_scope,  # type: ignore[arg-type]
            price_min_mxn=price_min_mxn,
            price_median_mxn=price_median_mxn,
            price_max_mxn=price_max_mxn,
            price_per_m2_median=round(float(median_ppm2), 2),
            comparables_used_ids=[c.id for c in survivors],
            methodology_note=note,
        )


@dataclass
class EngineRequest:
    """Compat wrapper used by services.valuation_service to invoke the engine."""

    city_id: int
    zone_id: Optional[int]
    property_type_id: int
    operation: str
    area_m2: float
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None


async def compute_valuation(
    session: AsyncSession, req: EngineRequest
) -> ValuationResult:
    """Thin functional wrapper around ValuationEngine.compute.

    Adapts the EngineRequest dataclass to the engine's keyword-only API and
    exposes a stable `comparable_ids` attribute alongside the original
    `comparables_used_ids` so the persistence layer can stay agnostic.
    """
    engine = ValuationEngine(session)
    result = await engine.compute(
        city_id=req.city_id,
        zone_id=req.zone_id,
        property_type_id=req.property_type_id,
        operation=req.operation,
        area_m2=req.area_m2,
    )
    # Frozen dataclass — set via object.__setattr__ to expose alias.
    object.__setattr__(result, "comparable_ids", result.comparables_used_ids)
    return result
