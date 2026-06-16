# KOKO Valuation API

API REST de valuación de propiedades para KOKO MLS. Calcula un rango de precio estimado (mediana ± banda) basado en comparables reales scrapeados de Inmuebles24 y Vivanuncios, segmentado por ciudad y zona. La consume el widget en la landing de KOKO para que un propietario reciba referencia inmediata sin que un agente intervenga.

**Regla no negociable — "cero datos inventados".** Si la zona o ciudad no tiene comparables suficientes (`confidence == "insuficiente"`), la respuesta omite `price_*` (campos en `null`) y `methodology_note` explica por qué. Es preferible decir "no sé" a inventar un número.

## Endpoints

| Método | Path | Descripción |
|---|---|---|
| POST | `/v1/valuation` | Calcula rango de valor de una propiedad |
| GET | `/v1/cities` | Lista ciudades activas |
| GET | `/v1/cities/{city_slug}/zones` | Zonas de una ciudad |
| GET | `/v1/property-types` | Tipos de propiedad soportados |
| GET | `/health` | Liveness simple |
| GET | `/health/ready` | Readiness profundo (DB + fuentes) |

Documentación interactiva: `/docs` (Swagger UI) y `/redoc`.

## Cómo correr localmente

Requisitos: Python 3.11+.

```bash
pip install -r requirements.txt   # o:  uv sync
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Una vez arriba: <http://localhost:8000/docs>.

### Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `DATABASE_URL` | — | Conexión async (postgresql+asyncpg://…) |
| `CORS_ORIGINS` | `*` | CSV de orígenes permitidos |
| `LOG_LEVEL` | `INFO` | Nivel de logging JSON |
| `API_KEY_REQUIRED` | `false` | Si está en `true`, `auth/` rechaza requests sin `X-API-Key` |

## Ejemplo: `POST /v1/valuation`

```bash
curl -X POST http://localhost:8000/v1/valuation \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $KOKO_API_KEY" \
  -d '{
    "city_slug": "tulum",
    "zone_slug": "aldea-zama",
    "property_type": "departamento",
    "operation": "venta",
    "area_m2": 80,
    "bedrooms": 2,
    "bathrooms": 2,
    "parking_spots": 1,
    "age_years": 3
  }'
```

### Respuesta con `confidence=alta`

```json
{
  "confidence": "alta",
  "price_min": 4500000,
  "price_max": 5800000,
  "price_median": 5100000,
  "price_per_m2_min": 56250,
  "price_per_m2_max": 72500,
  "price_per_m2_median": 63750,
  "currency": "MXN",
  "comparables_count": 12,
  "scope_used": "zone",
  "methodology_note": "Rango basado en mediana de precio/m² de 12 comparables vigentes en Aldea Zama, Tulum, ajustado por área de la propiedad consultada.",
  "disclaimer": "Esta es una referencia de mercado, no un avalúo profesional. Rango basado en 12 anuncios reales en Aldea Zama, Tulum.",
  "request_id": "req_01HXYZABC123",
  "computed_at": "2026-06-16T15:30:00Z"
}
```

### Respuesta con `confidence=insuficiente` (regla "cero datos inventados")

```json
{
  "confidence": "insuficiente",
  "price_min": null,
  "price_max": null,
  "price_median": null,
  "price_per_m2_min": null,
  "price_per_m2_max": null,
  "price_per_m2_median": null,
  "currency": "MXN",
  "comparables_count": 0,
  "scope_used": "zone",
  "methodology_note": "No se encontraron comparables vigentes para departamento de venta en la zona consultada ni en la ciudad. No se muestra estimación para evitar inventar un valor.",
  "disclaimer": "",
  "request_id": "req_01HXYZABC456",
  "computed_at": "2026-06-16T15:30:05Z"
}
```

Status `200` en ambos casos: la entrada fue válida; la API es honesta sobre la falta de datos.

## Niveles de confianza

| Comparables encontrados | `confidence` | Comportamiento |
|---|---|---|
| ≥ 8 | `alta` | Rango basado en mediana de la zona |
| 4–7 | `media` | Rango con menos certeza |
| 1–3 | `baja` | Rango ilustrativo, advertir al usuario |
| 0 | `insuficiente` | **Sin número**; `price_*` en `null` |

Si la zona consultada tiene menos de 4 comparables, el sistema amplía la búsqueda a la ciudad y baja un nivel de confianza. El campo `scope_used` indica el alcance final (`zone` o `city`).

## Headers y autenticación

- `X-API-Key` — requerido cuando `auth/` esté cableado. Hoy la dependencia opera en modo no-op (deja pasar) y emite warning en logs hasta que el especialista de auth termine.
- `X-Request-ID` — devuelto en cada respuesta para trazabilidad. Puede enviarse desde el cliente; si no, se genera uno (`req_<uuid>`).

## Errores

| Status | Cuándo |
|---|---|
| `200` | Éxito (incluido `confidence=insuficiente`) |
| `404` | `CityNotFoundError` — ciudad fuera del catálogo |
| `422` | Validación de entrada o `InvalidInputError` de dominio |
| `503` | `/health/ready` con dependencias caídas |

Todos los errores devuelven `{"detail": ..., "request_id": "..."}`.

## Disclaimer obligatorio

Cuando la respuesta trae estimación (`confidence != insuficiente`), `disclaimer` se rellena con:

> "Esta es una referencia de mercado, no un avalúo profesional. Rango basado en N anuncios reales en [zona/ciudad]."

Cuando no hay estimación, `disclaimer` sale vacío (no hay nada que enmarcar).

## Docker

Build context = raíz del repo (porque el contenedor también copia `services/`, `db/`, `auth/`):

```bash
docker build -t koko-valuation-api -f api/Dockerfile .
docker run --rm -p 8000:8000 --env-file .env koko-valuation-api
```

## Estructura

```
api/
├── main.py                 # FastAPI app, middleware, exception handlers
├── dependencies.py         # DB session, API key, rate limit
├── openapi_examples.py     # Ejemplos para Swagger (incluye disclaimer template)
├── routers/
│   ├── valuation.py        # POST /v1/valuation
│   ├── catalog.py          # GET /v1/cities, /zones, /property-types
│   └── health.py           # GET /health, /health/ready
├── Dockerfile
└── README.md
```
