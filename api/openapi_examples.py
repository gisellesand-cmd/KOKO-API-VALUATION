"""Ejemplos ricos para Swagger UI (request bodies y respuestas).

Centralizar aquí permite que los routers solo declaren OpenAPI metadata,
y que los ejemplos puedan revisarse junto al PRD (regla "cero datos inventados":
incluimos un ejemplo `insuficiente` para dejar explícito el contrato).
"""

from __future__ import annotations

DISCLAIMER_TEMPLATE = (
    "Esta es una referencia de mercado, no un avalúo profesional. "
    "Rango basado en {n} anuncios reales en {scope}."
)


def build_disclaimer(n: int, scope: str) -> str:
    return DISCLAIMER_TEMPLATE.format(n=n, scope=scope)


VALUATION_REQUEST_EXAMPLES: dict[str, dict] = {
    "depto_tulum_aldea_zama": {
        "summary": "Depto en Tulum / Aldea Zama (venta)",
        "description": "Caso típico: zona con cobertura. Devuelve confidence=alta.",
        "value": {
            "city_slug": "tulum",
            "zone_slug": "aldea-zama",
            "property_type": "departamento",
            "operation": "venta",
            "area_m2": 80,
            "bedrooms": 2,
            "bathrooms": 2,
            "parking_spots": 1,
            "age_years": 3,
        },
    },
    "casa_cancun": {
        "summary": "Casa en Cancún (sin zona)",
        "description": "Ciudad sin zona específica. Sistema busca a nivel ciudad.",
        "value": {
            "city_slug": "cancun",
            "zone_slug": None,
            "property_type": "casa",
            "operation": "venta",
            "area_m2": 220,
            "bedrooms": 4,
            "bathrooms": 3,
            "parking_spots": 2,
            "age_years": 8,
        },
    },
    "renta_depto_playa": {
        "summary": "Depto renta Playa del Carmen / Centro",
        "description": "Operación de renta.",
        "value": {
            "city_slug": "playa-del-carmen",
            "zone_slug": "centro",
            "property_type": "departamento",
            "operation": "renta",
            "area_m2": 60,
            "bedrooms": 1,
            "bathrooms": 1,
            "parking_spots": 1,
            "age_years": 5,
        },
    },
}


VALUATION_RESPONSE_EXAMPLES: dict[str, dict] = {
    "confidence_alta": {
        "summary": "confidence=alta (≥8 comparables en la zona)",
        "value": {
            "confidence": "alta",
            "price_min": 4_500_000,
            "price_max": 5_800_000,
            "price_median": 5_100_000,
            "price_per_m2_min": 56_250,
            "price_per_m2_max": 72_500,
            "price_per_m2_median": 63_750,
            "currency": "MXN",
            "comparables_count": 12,
            "scope_used": "zone",
            "methodology_note": (
                "Rango basado en mediana de precio/m² de 12 comparables vigentes "
                "en Aldea Zama, Tulum, ajustado por área de la propiedad consultada."
            ),
            "disclaimer": build_disclaimer(12, "Aldea Zama, Tulum"),
            "request_id": "req_01HXYZABC123",
            "computed_at": "2026-06-16T15:30:00Z",
        },
    },
    "confidence_insuficiente": {
        "summary": "confidence=insuficiente (0 comparables, sin estimación)",
        "value": {
            "confidence": "insuficiente",
            "price_min": None,
            "price_max": None,
            "price_median": None,
            "price_per_m2_min": None,
            "price_per_m2_max": None,
            "price_per_m2_median": None,
            "currency": "MXN",
            "comparables_count": 0,
            "scope_used": "zone",
            "methodology_note": (
                "No se encontraron comparables vigentes para departamento de venta "
                "en la zona consultada ni en la ciudad. No se muestra estimación "
                "para evitar inventar un valor."
            ),
            "disclaimer": "",
            "request_id": "req_01HXYZABC456",
            "computed_at": "2026-06-16T15:30:05Z",
        },
    },
    "fallback_a_ciudad": {
        "summary": "fallback: zona sin volumen, se amplía a ciudad → confidence=media",
        "value": {
            "confidence": "media",
            "price_min": 3_800_000,
            "price_max": 5_200_000,
            "price_median": 4_400_000,
            "price_per_m2_min": 47_500,
            "price_per_m2_max": 65_000,
            "price_per_m2_median": 55_000,
            "currency": "MXN",
            "comparables_count": 6,
            "scope_used": "city",
            "methodology_note": (
                "La zona consultada tenía menos de 4 comparables; se amplió la "
                "búsqueda a toda la ciudad. Confianza media basada en 6 "
                "comparables a nivel ciudad."
            ),
            "disclaimer": build_disclaimer(6, "Tulum"),
            "request_id": "req_01HXYZABC789",
            "computed_at": "2026-06-16T15:30:10Z",
        },
    },
}


CITIES_RESPONSE_EXAMPLE: dict = {
    "summary": "Ciudades activas",
    "value": [
        {"slug": "tulum", "name": "Tulum", "state": "Quintana Roo", "is_active": True},
        {"slug": "cancun", "name": "Cancún", "state": "Quintana Roo", "is_active": True},
        {
            "slug": "playa-del-carmen",
            "name": "Playa del Carmen",
            "state": "Quintana Roo",
            "is_active": True,
        },
    ],
}


ZONES_RESPONSE_EXAMPLE: dict = {
    "summary": "Zonas de Tulum",
    "value": [
        {"slug": "aldea-zama", "name": "Aldea Zamá", "city_slug": "tulum"},
        {"slug": "region-15", "name": "Región 15", "city_slug": "tulum"},
        {"slug": "la-veleta", "name": "La Veleta", "city_slug": "tulum"},
    ],
}


PROPERTY_TYPES_RESPONSE_EXAMPLE: dict = {
    "summary": "Tipos de propiedad disponibles",
    "value": [
        {"slug": "departamento", "label": "Departamento"},
        {"slug": "casa", "label": "Casa"},
        {"slug": "terreno", "label": "Terreno"},
        {"slug": "local", "label": "Local comercial"},
    ],
}


HEALTH_OK_EXAMPLE: dict = {
    "summary": "Liveness OK",
    "value": {"status": "ok"},
}


HEALTH_READY_EXAMPLE: dict = {
    "summary": "Readiness OK",
    "value": {
        "status": "ok",
        "checks": {
            "database": "ok",
            "comparables_freshness": "ok",
        },
    },
}


VALIDATION_ERROR_EXAMPLE: dict = {
    "summary": "Error de validación de entrada",
    "value": {
        "detail": [
            {
                "loc": ["body", "area_m2"],
                "msg": "Input should be greater than 0",
                "type": "greater_than",
            }
        ],
        "request_id": "req_01HXYZABC999",
    },
}


CITY_NOT_FOUND_EXAMPLE: dict = {
    "summary": "Ciudad no encontrada",
    "value": {
        "detail": "Ciudad no encontrada: monterrey",
        "request_id": "req_01HXYZABC000",
    },
}
