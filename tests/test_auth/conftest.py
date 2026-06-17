from __future__ import annotations

from types import SimpleNamespace

import pytest


@pytest.fixture
def fake_api_key():
    return SimpleNamespace(
        id=1,
        name="test",
        tier="free",
        key_hash="$argon2id$placeholder",
        key_prefix="kmls_aB3xY7s...",
        active=True,
        revoked_at=None,
        requests_per_day=100,
    )


@pytest.fixture
def fake_paid_api_key():
    return SimpleNamespace(
        id=2,
        name="paid",
        tier="paid",
        key_hash="$argon2id$placeholder",
        key_prefix="kmls_paid01...",
        active=True,
        revoked_at=None,
        requests_per_day=10000,
    )


@pytest.fixture
def fake_db_session():
    class _Session:
        async def execute(self, *a, **kw):
            class _R:
                def scalars(self_inner):
                    return iter([])
            return _R()
    return _Session()
