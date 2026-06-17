"""Router de valuación. POST /v1/valuation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

from api.dependencies import get_api_key, get_db_session, rate_limit_dependency
from api.openapi_examples import (
    CITY_NOT_FOUND_EXAMPLE,
    VALIDATION_ERROR_EXAMPLE,
    VALUATION_REQUEST_EXAMPLES,
    VALUATION_RESPONSE_EXAMPLES,
)

try:
    from services.schemas import ValuationInput, ValuationOutput  # type: ignore
    from services.valuation_service import request_valuation  # type: ignore
except Exception:  # noqa: BLE001
    ValuationInput = Any  # type: ignore[assignment,misc]
    ValuationOutput = Any  # type: ignore[assignment,misc]

    async def request_valuation(payload, db):  # type: ignore[no-redef]
        raise RuntimeError(
            "services.valuation_service.request_valuation no está disponible. "
            "Otro especialista debe proveer services/."
        )


router = APIRouter(prefix="/v1", tags=["Valuación"])


@router.post(
    "/valuation",
    response_model=ValuationOutput,
    summary="Calcula rango de valor de una propiedad",
    description=(
        "Devuelve un rango estimado de precio (min/max/mediana) y precio por m² "
        "basado en comparables vigentes en la zona o ciudad consultada.\n\n"
        "**Niveles de confianza**: `alta` (≥8 comparables), `media` (4–7), "
        "`baja` (1–3), `insuficiente` (0).\n\n"
        "**Fallback**: si la zona no tiene volumen suficiente, el servicio "
        "amplía la búsqueda a la ciudad completa y baja el nivel de confianza "
        "para reflejarlo (`scope_used` indica el alcance final).\n\n"
        "**Regla 'cero datos inventados'**: si `confidence == \"insuficiente\"` "
        "los campos `price_*` salen en `null` y `methodology_note` explica por "
        "qué. El status sigue siendo `200` porque la entrada fue válida; "
        "la respuesta refleja honestamente la falta de datos."
    ),
    responses={
        200: {
            "description": "Valuación calculada (con o sin estimación numérica).",
            "content": {
                "application/json": {
                    "examples": VALUATION_RESPONSE_EXAMPLES,
                }
            },
        },
        404: {
            "description": "Ciudad no encontrada en el catálogo.",
            "content": {"application/json": {"examples": {"city_not_found": CITY_NOT_FOUND_EXAMPLE}}},
        },
        422: {
            "description": "Entrada inválida.",
            "content": {"application/json": {"examples": {"validation": VALIDATION_ERROR_EXAMPLE}}},
        },
    },
)
async def post_valuation(
    payload: ValuationInput = Body(..., openapi_examples=VALUATION_REQUEST_EXAMPLES),
    db=Depends(get_db_session),
    _api_key: str | None = Depends(get_api_key),
    _rl: None = Depends(rate_limit_dependency),
):
    return await request_valuation(payload, db)
