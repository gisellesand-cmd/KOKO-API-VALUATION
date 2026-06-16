"""Dependencias FastAPI compartidas: sesión DB, API key, rate limit.

Las piezas de auth y persistencia las construyen otros especialistas
(`auth/`, `db/`). Aquí solo proveemos el cableado y degradamos con un
no-op claro mientras esos módulos no estén disponibles.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import Header, HTTPException, status

log = logging.getLogger(__name__)


try:
    from db.session import get_session as _db_get_session  # type: ignore
except Exception:  # ImportError o errores aguas abajo
    _db_get_session = None


try:
    from auth.api_key import verify_api_key as _verify_api_key  # type: ignore
except Exception:
    _verify_api_key = None
    log.warning(
        "auth.api_key no disponible: la dependencia get_api_key opera en modo no-op "
        "(permite todas las requests). TODO: cablear cuando auth/ esté listo."
    )


try:
    from auth.rate_limit import enforce_rate_limit as _enforce_rate_limit  # type: ignore
except Exception:
    _enforce_rate_limit = None


async def get_db_session() -> AsyncGenerator[Any, None]:
    """Sesión async de DB. Se delega a `db.session.get_session`."""
    if _db_get_session is None:
        raise RuntimeError(
            "db.session.get_session no está disponible. "
            "Otro especialista debe proveer el módulo db/."
        )
    async for session in _db_get_session():
        yield session


async def get_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str | None:
    """Verifica X-API-Key si auth/api_key.py está disponible.

    Mientras no exista el módulo de auth, no bloquea para no frenar el
    desarrollo de la API. El operador debe vigilar que auth se cablee
    antes de exponer el servicio a internet.
    """
    if _verify_api_key is None:
        # TODO: cablear auth/api_key.py cuando el especialista de auth termine.
        return None
    try:
        return await _verify_api_key(x_api_key)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida.",
        ) from exc


async def rate_limit_dependency(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """Aplica rate limit si auth/rate_limit.py está disponible."""
    if _enforce_rate_limit is None:
        # TODO: cablear auth/rate_limit.py cuando esté listo.
        return None
    await _enforce_rate_limit(x_api_key)
    return None
