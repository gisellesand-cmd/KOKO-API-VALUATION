"""FastAPI dependencies for API key authentication and caller tier resolution."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from fastapi import Depends, Header, HTTPException, status

from auth.api_key import get_api_key_from_db

if TYPE_CHECKING:
    from db.models.api_key import ApiKey

try:
    from db.session import get_db_session
except ImportError:
    async def get_db_session():
        # Placeholder until the database specialist wires this up. Raising on
        # call (rather than import) keeps auth.* importable in CI and tests.
        raise NotImplementedError(
            "db.session.get_db_session is not yet implemented. "
            "Wire it up before using auth dependencies against a real DB."
        )
        yield  # pragma: no cover


_UNAUTHENTICATED_HEADERS = {"WWW-Authenticate": "ApiKey"}


async def get_current_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    session=Depends(get_db_session),
) -> Optional["ApiKey"]:
    if x_api_key is None:
        return None
    plain = x_api_key.strip()
    if not plain:
        return None

    api_key = await get_api_key_from_db(plain, session)
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
            headers=_UNAUTHENTICATED_HEADERS,
        )
    return api_key


async def require_api_key(
    api_key: Optional["ApiKey"] = Depends(get_current_api_key),
) -> "ApiKey":
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
            headers=_UNAUTHENTICATED_HEADERS,
        )
    return api_key


def get_caller_tier(
    api_key: Optional["ApiKey"] = Depends(get_current_api_key),
) -> str:
    if api_key is None:
        return "public"
    return api_key.tier
