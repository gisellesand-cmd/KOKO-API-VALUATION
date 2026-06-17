"""API key hashing, generation, and lookup.

Keys are issued with the ``kmls_`` prefix so they're recognizable in logs and
support tickets. We hash with argon2 (via passlib) and never store the plain
key. The argon2 calls are CPU-bound; we offload them to a thread so they
don't block the event loop.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from typing import TYPE_CHECKING, Optional

from passlib.context import CryptContext

if TYPE_CHECKING:
    from db.models.api_key import ApiKey

logger = logging.getLogger(__name__)

_KEY_PREFIX = "kmls_"
_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


async def hash_api_key(plain: str) -> str:
    return await asyncio.to_thread(_pwd_context.hash, plain)


async def verify_api_key(plain: str, hash: str) -> bool:
    try:
        return await asyncio.to_thread(_pwd_context.verify, plain, hash)
    except Exception:
        # passlib raises on malformed hashes; treat as a failed verify.
        return False


async def generate_api_key() -> tuple[str, str]:
    plain = _KEY_PREFIX + secrets.token_urlsafe(32)
    hashed = await hash_api_key(plain)
    return plain, hashed


async def get_api_key_from_db(plain: str, session) -> Optional["ApiKey"]:
    # NOTE: argon2 hashes are salted and non-deterministic, so we can't query
    # by hash equality. We fetch active/non-revoked rows and verify_api_key
    # each one. This is O(N) over active keys; if N gets large, add a
    # deterministic short-lookup-prefix column to ApiKey and filter on it
    # first.
    try:
        from sqlalchemy import select

        from db.models.api_key import ApiKey
    except ImportError:
        logger.debug("db.models.api_key not available; returning None")
        return None

    stmt = select(ApiKey).where(ApiKey.active.is_(True), ApiKey.revoked_at.is_(None))
    result = await session.execute(stmt)
    for row in result.scalars():
        if await verify_api_key(plain, row.key_hash):
            return row
    return None
