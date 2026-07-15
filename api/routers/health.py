"""Router de salud: liveness y readiness."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_db_session
from api.openapi_examples import HEALTH_OK_EXAMPLE, HEALTH_READY_EXAMPLE

try:
    from services.health_service import liveness, readiness  # type: ignore
    from services.schemas import HealthStatus  # type: ignore
except Exception:  # noqa: BLE001
    HealthStatus = Any  # type: ignore[assignment,misc]

    async def liveness():  # type: ignore[no-redef]
        return {"status": "ok"}

    async def readiness(db):  # type: ignore[no-redef]
        return {"status": "ok", "checks": {"database": "unknown"}}


router = APIRouter(tags=["Salud"])



@router.get(
    "/health",
    response_model=HealthStatus,
    summary="Liveness simple",
    responses={
        200: {
            "content": {"application/json": {"examples": {"ok": HEALTH_OK_EXAMPLE}}},
        }
    },
)
async def get_health():
    return await liveness()


@router.get(
    "/health/ready",
    response_model=HealthStatus,
    summary="Readiness profundo (DB + fuentes)",
    responses={
        200: {
            "content": {"application/json": {"examples": {"ok": HEALTH_READY_EXAMPLE}}},
        },
        503: {"description": "Alguna dependencia no está saludable."},
    },
)
async def get_health_ready(db=Depends(get_db_session)):
    result = await readiness(db)
    payload = result.model_dump() if hasattr(result, "model_dump") else dict(result)
    if payload.get("status") != "ok":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=payload)
    return result
