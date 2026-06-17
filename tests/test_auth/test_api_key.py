from __future__ import annotations

import pytest

from auth.api_key import generate_api_key, hash_api_key, verify_api_key

pytestmark = pytest.mark.asyncio


async def test_hash_then_verify_roundtrip():
    hashed = await hash_api_key("kmls_secret_value")
    assert await verify_api_key("kmls_secret_value", hashed) is True


async def test_verify_rejects_wrong_plain():
    hashed = await hash_api_key("kmls_secret_value")
    assert await verify_api_key("kmls_wrong_value", hashed) is False


async def test_verify_handles_garbage_hash():
    assert await verify_api_key("anything", "not-a-hash") is False


async def test_generate_api_key_format():
    plain, hashed = await generate_api_key()
    assert plain.startswith("kmls_")
    assert len(plain) >= 30
    assert hashed.startswith("$argon2")


async def test_generate_api_key_unique():
    p1, h1 = await generate_api_key()
    p2, h2 = await generate_api_key()
    assert p1 != p2
    assert h1 != h2
