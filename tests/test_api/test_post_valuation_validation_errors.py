"""
Integration tests for ``POST /v1/valuation`` — Pydantic validation errors.

Rules verified:
  * Missing required fields produce HTTP 422 with a structured ``detail``
    list whose entries carry ``loc``, ``msg`` and ``type`` (FastAPI default).
  * Numeric fields enforce positive constraints.
  * Wrong types and unknown enum values are rejected with 422.
  * Every 422 response is JSON.
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_missing_city_slug_returns_422(api_client, auth_headers):
    response = await api_client.post(
        "/v1/valuation",
        headers=auth_headers,
        json={"property_type": "casa", "area_m2": 200},
    )
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")
    detail = response.json()["detail"]
    assert isinstance(detail, list) and detail
    assert detail[0]["loc"] == ["body", "city_slug"]
    assert detail[0]["type"] == "missing"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_negative_area_returns_422(api_client, auth_headers):
    response = await api_client.post(
        "/v1/valuation",
        headers=auth_headers,
        json={"city_slug": "tulum", "property_type": "casa", "area_m2": -10},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    msgs = " ".join(item.get("msg", "").lower() for item in detail)
    assert "greater than" in msgs or "positive" in msgs or "0" in msgs


@pytest.mark.integration
@pytest.mark.asyncio
async def test_non_numeric_area_returns_422(api_client, auth_headers):
    response = await api_client.post(
        "/v1/valuation",
        headers=auth_headers,
        json={"city_slug": "tulum", "property_type": "casa", "area_m2": "abc"},
    )
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invalid_property_type_enum_returns_422(api_client, auth_headers):
    response = await api_client.post(
        "/v1/valuation",
        headers=auth_headers,
        json={
            "city_slug": "tulum",
            "property_type": "invalid_type",
            "area_m2": 200,
        },
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any(item.get("loc", [])[-1] == "property_type" for item in detail)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_empty_body_returns_422_with_multiple_missing(api_client, auth_headers):
    response = await api_client.post("/v1/valuation", headers=auth_headers, json={})
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    missing_locs = {tuple(item["loc"]) for item in detail if item.get("type") == "missing"}
    assert ("body", "city_slug") in missing_locs
    assert len(missing_locs) >= 2
