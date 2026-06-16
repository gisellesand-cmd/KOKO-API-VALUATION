"""Router de catálogo: ciudades, zonas y tipos de propiedad."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Path

from api.dependencies import get_api_key, get_db_session, rate_limit_dependency
from api.openapi_examples import (
    CITIES_RESPONSE_EXAMPLE,
    CITY_NOT_FOUND_EXAMPLE,
    PROPERTY_TYPES_RESPONSE_EXAMPLE,
    ZONES_RESPONSE_EXAMPLE,
)

try:
    from services.catalog_service import (  # type: ignore
        list_cities,
        list_property_types,
        list_zones,
    )
    from services.schemas import City, PropertyType, Zone  # type: ignore
except Exception:  # noqa: BLE001
    City = Any  # type: ignore[assignment,misc]
    Zone = Any  # type: ignore[assignment,misc]
    PropertyType = Any  # type: ignore[assignment,misc]

    async def list_cities(db):  # type: ignore[no-redef]
        raise RuntimeError("services.catalog_service.list_cities no disponible.")

    async def list_zones(city_slug, db):  # type: ignore[no-redef]
        raise RuntimeError("services.catalog_service.list_zones no disponible.")

    async def list_property_types(db):  # type: ignore[no-redef]
        raise RuntimeError("services.catalog_service.list_property_types no disponible.")


router = APIRouter(prefix="/v1", tags=["Catálogo"])


@router.get(
    "/cities",
    response_model=list[City],
    summary="Lista ciudades activas",
    responses={
        200: {
            "description": "Ciudades cubiertas por el sistema.",
            "content": {"application/json": {"examples": {"cities": CITIES_RESPONSE_EXAMPLE}}},
        }
    },
)
async def get_cities(
    db=Depends(get_db_session),
    _api_key: str | None = Depends(get_api_key),
    _rl: None = Depends(rate_limit_dependency),
):
    cities = await list_cities(db)
    return [c for c in cities if getattr(c, "is_active", True)]


@router.get(
    "/cities/{city_slug}/zones",
    response_model=list[Zone],
    summary="Lista zonas de una ciudad",
    responses={
        200: {
            "description": "Zonas registradas para la ciudad.",
            "content": {"application/json": {"examples": {"zones": ZONES_RESPONSE_EXAMPLE}}},
        },
        404: {
            "description": "Ciudad no encontrada.",
            "content": {"application/json": {"examples": {"city_not_found": CITY_NOT_FOUND_EXAMPLE}}},
        },
    },
)
async def get_zones(
    city_slug: str = Path(..., examples=["tulum"]),
    db=Depends(get_db_session),
    _api_key: str | None = Depends(get_api_key),
    _rl: None = Depends(rate_limit_dependency),
):
    return await list_zones(city_slug, db)


@router.get(
    "/property-types",
    response_model=list[PropertyType],
    summary="Lista tipos de propiedad soportados",
    responses={
        200: {
            "description": "Tipos disponibles.",
            "content": {
                "application/json": {
                    "examples": {"property_types": PROPERTY_TYPES_RESPONSE_EXAMPLE}
                }
            },
        }
    },
)
async def get_property_types(
    db=Depends(get_db_session),
    _api_key: str | None = Depends(get_api_key),
    _rl: None = Depends(rate_limit_dependency),
):
    return await list_property_types(db)
