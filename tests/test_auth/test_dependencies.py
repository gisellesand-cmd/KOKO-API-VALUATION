from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from auth import dependencies as deps

pytestmark = pytest.mark.asyncio


async def test_get_current_api_key_returns_none_when_header_absent(monkeypatch, fake_db_session):
    monkeypatch.setattr(deps, "get_api_key_from_db", AsyncMock())
    result = await deps.get_current_api_key(x_api_key=None, session=fake_db_session)
    assert result is None
    deps.get_api_key_from_db.assert_not_called()


async def test_get_current_api_key_returns_none_for_empty_string(monkeypatch, fake_db_session):
    monkeypatch.setattr(deps, "get_api_key_from_db", AsyncMock())
    result = await deps.get_current_api_key(x_api_key="   ", session=fake_db_session)
    assert result is None


async def test_get_current_api_key_raises_401_when_invalid(monkeypatch, fake_db_session):
    monkeypatch.setattr(deps, "get_api_key_from_db", AsyncMock(return_value=None))
    with pytest.raises(HTTPException) as exc:
        await deps.get_current_api_key(x_api_key="kmls_bad", session=fake_db_session)
    assert exc.value.status_code == 401


async def test_get_current_api_key_returns_apikey_when_valid(
    monkeypatch, fake_db_session, fake_api_key
):
    monkeypatch.setattr(deps, "get_api_key_from_db", AsyncMock(return_value=fake_api_key))
    result = await deps.get_current_api_key(x_api_key="kmls_good", session=fake_db_session)
    assert result is fake_api_key


async def test_require_api_key_raises_401_when_none():
    with pytest.raises(HTTPException) as exc:
        await deps.require_api_key(api_key=None)
    assert exc.value.status_code == 401


async def test_require_api_key_returns_when_present(fake_api_key):
    result = await deps.require_api_key(api_key=fake_api_key)
    assert result is fake_api_key


def test_get_caller_tier_public_when_none():
    assert deps.get_caller_tier(api_key=None) == "public"


def test_get_caller_tier_uses_tier_attribute(fake_paid_api_key):
    assert deps.get_caller_tier(api_key=fake_paid_api_key) == "paid"
