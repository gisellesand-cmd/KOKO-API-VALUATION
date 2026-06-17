"""
Integration tests for CORS configuration.

Rules verified:
  * Preflight ``OPTIONS`` requests from the widget host receive a 200/204
    response with ``access-control-allow-origin`` set (wildcard or echoed
    origin) and ``access-control-allow-methods`` listing the requested verb.
  * Actual requests (POST /v1/valuation, GET /v1/cities) include
    ``access-control-allow-origin`` so browser-side widgets can read the
    response.
"""

from __future__ import annotations

import pytest

from tests.factories import (
    PropertyTypeFactory,
    TulumCityFactory,
    ZoneFactory,
)

WIDGET_ORIGIN = "https://widget.koko.mx"


def _origin_allows(header_value: str | None, origin: str) -> bool:
    return header_value is not None and (header_value == "*" or header_value == origin)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_preflight_valuation_allows_widget_origin(api_client):
    response = await api_client.options(
        "/v1/valuation",
        headers={
            "Origin": WIDGET_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-api-key",
        },
    )
    assert response.status_code in (200, 204)
    assert _origin_allows(response.headers.get("access-control-allow-origin"), WIDGET_ORIGIN)
    allow_methods = response.headers.get("access-control-allow-methods", "")
    assert "POST" in allow_methods.upper()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_actual_post_valuation_carries_cors_header(
    api_client, async_session, auth_headers
):
    city = TulumCityFactory()
    ZoneFactory(city=city, name="Aldea Zama", slug="aldea-zama")
    PropertyTypeFactory(slug="casa")

    response = await api_client.post(
        "/v1/valuation",
        headers={**auth_headers, "Origin": WIDGET_ORIGIN},
        json={
            "city_slug": "tulum",
            "zone_slug": "aldea-zama",
            "property_type": "casa",
            "area_m2": 200,
        },
    )
    assert response.status_code in (200, 404)  # 404 only if seed failed; CORS still required
    assert _origin_allows(response.headers.get("access-control-allow-origin"), WIDGET_ORIGIN)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_preflight_cities_allows_widget_origin(api_client):
    response = await api_client.options(
        "/v1/cities",
        headers={
            "Origin": WIDGET_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code in (200, 204)
    assert _origin_allows(response.headers.get("access-control-allow-origin"), WIDGET_ORIGIN)
    allow_methods = response.headers.get("access-control-allow-methods", "")
    assert "GET" in allow_methods.upper()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_actual_get_cities_carries_cors_header(api_client, auth_headers):
    response = await api_client.get(
        "/v1/cities",
        headers={**auth_headers, "Origin": WIDGET_ORIGIN},
    )
    assert response.status_code == 200
    assert _origin_allows(response.headers.get("access-control-allow-origin"), WIDGET_ORIGIN)
