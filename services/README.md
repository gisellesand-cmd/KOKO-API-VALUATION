# services/ — KOKO MLS backend services layer

## Purpose

The `services/` package is the orchestration layer for the KOKO MLS Property Valuation API. It mediates between the FastAPI routes (HTTP edge) and the pure-Python pricing engine (`valuation/`) + persistence layer (`db/`). The single, non-negotiable rule of this layer is **"Cero datos inventados"**: every numeric value returned to a client must be traceable to real `Comparable` rows pulled from the database, and every response is audited via a paired `ValuationRequest` + `ValuationResponse` record whose `comparable_ids` JSON column lists the exact rows used.

## Architecture

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌──────────┐
│   FastAPI   │───▶│   services/      │───▶│  valuation/     │───▶│  db/     │
│   routes    │    │   (orchestrator) │    │  engine.py      │    │ (SQLAlc) │
└─────────────┘    └──────────────────┘    └─────────────────┘    └──────────┘
                           │                                            ▲
                           └─── persists Request+Response audit ────────┘
```

## Module map

| File                  | Responsibility                                                                     |
|-----------------------|------------------------------------------------------------------------------------|
| `schemas.py`          | Pydantic v2 DTOs (`ValuationInput`, `ValuationOutput`, catalog DTOs, `HealthCheckResult`) + `DISCLAIMER_TEXT`. |
| `exceptions.py`       | Domain exceptions (`CityNotFoundError`, `ZoneNotFoundError`, `PropertyTypeNotFoundError`, `InvalidInputError`, `InsufficientDataError`). |
| `config.py`           | `Settings` (pydantic-settings) + cached `get_settings()`. Sources `.env`.          |
| `logging.py`          | Structlog setup + `bind_request_id` / `clear_request_context` helpers.             |
| `valuation_service.py`| `request_valuation()`: catalog lookup → comparables query → engine → persistence.  |
| `catalog_service.py`  | `list_cities` / `list_zones` / `list_property_types` with in-process 5-min TTL cache + `invalidate_catalog_cache`. |
| `health_service.py`   | `check_health()`: pings DB, counts comparables per city, reports last scrape per portal. |

## Request flow (`request_valuation`)

1. Validate input via `ValuationInput` (pydantic).
2. Resolve `city_slug` → `City` (raise `CityNotFoundError` on miss).
3. If `zone_slug` provided, resolve `Zone` (raise `ZoneNotFoundError` on miss).
4. Resolve `property_type_slug` → `PropertyType` (raise `PropertyTypeNotFoundError` on miss).
5. Query `Comparable` rows matching {city, zone?, property_type, operation, is_active=True}.
6. If < N comparables at zone level, widen to city scope and re-query.
7. Hand the result set to `valuation.engine.compute_valuation()` for percentile + confidence math.
8. Persist a `ValuationRequest` row + a `ValuationResponse` row whose `comparable_ids` column is the JSON list of IDs that fed the calculation.
9. Return a `ValuationOutput` with the disclaimer attached.

## Audit guarantee

Every response is paired with a `ValuationResponse.comparable_ids` JSON array — the exact primary keys of `Comparable` rows that produced `price_median_mxn`, `price_min_mxn`, `price_max_mxn`, etc. This is the single source of truth for "why did the API return this number?" and is the backbone of the "Cero datos inventados" rule. If the engine cannot find enough rows, it returns `confidence_level="insuficiente"` and **all price fields are `None`** — never estimated, never imputed.

## Caching

- `catalog_service` keeps a process-local 5-minute TTL cache for cities / zones / property types.
- Use `catalog_service.invalidate_catalog_cache()` after admin writes or scraper batches.
- No caching is applied to valuation results (every request is audited).

## Health status taxonomy

- `ok` — DB reachable, comparables present, last successful scrape per active portal within 7 days.
- `degraded` — DB reachable but at least one portal hasn't scraped successfully in > 7 days, or some cities have zero comparables.
- `down` — DB unreachable.

## Config & env

Service configuration is loaded from environment variables. See `.env.example` at repo root for the full set:

- `DATABASE_URL` — async SQLAlchemy URL (asyncpg for prod, aiosqlite for tests).
- `ENVIRONMENT` — `dev` / `staging` / `prod` / `test`.
- `LOG_LEVEL` — standard Python logging level.
- `CORS_ORIGINS` — comma-separated list consumed by the FastAPI app.

## Tests

```bash
pytest -q tests/test_services
```

The test suite uses in-memory SQLite via `aiosqlite` and has no external dependencies — no Postgres, no network. See `tests/conftest.py` for fixtures (`session`, `seeded_catalog`, `seed_comparables`, `patched_session_factory`).
