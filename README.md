# KOKO MLS — API de Valuación de Propiedades

API de valuación automatizada de inmuebles en México. Calcula precios estimados de propiedades a partir de comparables obtenidos de portales inmobiliarios (Vivanuncios) y ajusta por tipo de cambio usando el SIE de Banxico. Expone endpoints REST para consultar valuaciones, comparables y métricas de mercado.

## Stack
- Python 3.11, FastAPI, asyncpg
- Postgres 15 (con migraciones Alembic)
- Redis 7 (rate limit + cache)
- Scrapers: Vivanuncios (cada 6h), Banxico SIE (FX diario)
- Deploy: Fly.io (Querétaro)

## Desarrollo local

Requisitos: Docker Desktop, `make`, `git`.

Pasos:

1. `cp .env.example .env.local` y edita lo necesario (al menos `BANXICO_API_TOKEN`).
2. `make dev` (levanta `api` + `postgres` + `redis` + `scrapers-worker` en docker-compose).
3. API en http://localhost:8080, docs interactivas en http://localhost:8080/docs.
4. `make migrate` para aplicar migraciones, `make seed` para datos de referencia (catálogos de colonias, tipos de propiedad, FX inicial).

Para detener el stack: `make dev-down`. Para limpiar volúmenes (destructivo): `make dev-clean`.

## Variables de entorno

Todas las variables viven en `.env.example`. En local se cargan desde `.env.local`; en producción se setean como Fly secrets.

| Variable | Descripción | Default | Requerida en prod |
|---|---|---|---|
| `ENVIRONMENT` | Entorno de ejecución (`local`, `staging`, `production`). | `local` | Sí |
| `LOG_LEVEL` | Nivel de logging (`DEBUG`, `INFO`, `WARNING`, `ERROR`). | `INFO` | Sí |
| `DATABASE_URL` | DSN de Postgres (`postgresql+asyncpg://user:pass@host:5432/db`). | `postgresql+asyncpg://koko:koko@postgres:5432/koko_mls` | Sí (inyectada por Fly Postgres) |
| `REDIS_URL` | URL de Redis (`redis://host:6379/0`). | `redis://redis:6379/0` | Sí |
| `CORS_ORIGINS` | Lista de orígenes permitidos, separados por coma. | `http://localhost:3000` | Sí |
| `BANXICO_API_TOKEN` | Token del SIE de Banxico para consultar FX. | — | Sí |
| `VIVANUNCIOS_RATE_LIMIT_RPS` | Requests por segundo contra Vivanuncios. | `0.5` | Sí |
| `SCRAPER_INTERVAL_HOURS` | Frecuencia del scraper de comparables. | `6` | Sí |
| `SENTRY_DSN` | DSN de Sentry para reporte de errores. | — | Recomendada |
| `FLY_API_TOKEN` | Token de Fly.io para deploys desde CI. | — | Solo CI |
| `BACKUP_S3_BUCKET` | Bucket S3 destino de backups de Postgres. | — | Sí (en `scrapers`) |
| `AWS_ACCESS_KEY_ID` | Credencial IAM para subir backups a S3. | — | Sí (en `scrapers`) |
| `AWS_SECRET_ACCESS_KEY` | Secret de la credencial IAM. | — | Sí (en `scrapers`) |
| `AWS_REGION` | Región AWS del bucket de backups. | `us-east-1` | Sí (en `scrapers`) |

## Migraciones (Alembic)

- Crear nueva revisión: `make migrate-new MSG="add comparables index"` → corre `alembic revision --autogenerate -m "..."`.
- Aplicar en local: `make migrate`.
- Revertir una revisión: `make migrate-down`.
- En producción se corre automáticamente vía `release_command` en `fly.toml`, que invoca `infra/migrate.sh` antes de promover la nueva versión.

## Deploy a Fly.io

Una sola vez (setup inicial):

```
fly auth login
fly apps create koko-valuation-api --org koko
fly apps create koko-valuation-scrapers --org koko
fly postgres create --name koko-mls-db --region qro
fly redis create --name koko-mls-redis --region qro
fly postgres attach koko-mls-db --app koko-valuation-api
fly secrets set --app koko-valuation-api BANXICO_API_TOKEN=... SENTRY_DSN=... CORS_ORIGINS=... REDIS_URL=...
fly secrets set --app koko-valuation-scrapers (mismas)
fly volumes create koko_api_data --region qro --size 1 --app koko-valuation-api
```

En cada PR mergeado a `main`, GitHub Actions corre `fly deploy` automáticamente (workflow `.github/workflows/ci.yml`).

Deploy manual: `make deploy` (despliega API + scrapers). Para uno solo: `make deploy-api` o `make deploy-scrapers`.

## Rotar API keys

- **Banxico**: pedir nuevo token en https://www.banxico.org.mx/SieAPIRest/service/v1/token, luego:
  ```
  fly secrets set BANXICO_API_TOKEN=... --app koko-valuation-api
  fly secrets set BANXICO_API_TOKEN=... --app koko-valuation-scrapers
  ```
- **Sentry**: rotar DSN en sentry.io, después `fly secrets set SENTRY_DSN=... --app koko-valuation-api`.
- **AWS para backups**: rotar IAM keys en la consola de AWS, después:
  ```
  fly secrets set AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... --app koko-valuation-scrapers
  ```
- Después de rotar cualquier secret, corre `fly deploy` para forzar reinicio (o `fly machine restart`).

## Monitoreo

- Logs estructurados (JSON) a stdout — `make logs` para local, `make logs-prod` o `fly logs --app koko-valuation-api` para producción.
- Métricas Prometheus en `/metrics` (Fly los scrapea automáticamente si la sección `[metrics]` está en `fly.toml`).
- Sentry opcional vía `SENTRY_DSN`.
- Dashboard de Grafana en `monitoring/grafana-dashboard.json` (importar a tu instancia de Grafana).

## Backups

- `infra/backup.sh` corre semanal vía cron en `koko-valuation-scrapers` (configurado en `infra/crontab`) y sube un dump de Postgres a S3 (`BACKUP_S3_BUCKET`).
- Para correr ad-hoc localmente: `make backup` (requiere AWS creds en `.env.local`).
- Retención: 12 semanas en S3 con lifecycle policy en el bucket.

## Estructura del repo

```
.
├── api/                    # FastAPI app (routers, schemas, servicios, deps)
├── db/                     # Modelos SQLAlchemy + migraciones Alembic
│   └── alembic/
├── scrapers/               # Workers de Vivanuncios y Banxico
├── tests/                  # Pytest (unit + integración)
├── infra/                  # Scripts de migrate, seed, backup, crontab
├── monitoring/             # Dashboards Grafana, reglas Prometheus
├── docker-compose.yml      # Stack local
├── Dockerfile              # Imagen producción (api + scrapers)
├── fly.toml                # Config Fly para API
├── fly-scrapers.toml       # Config Fly para workers de scrapers
├── .env.example            # Plantilla de variables
└── Makefile                # Tareas comunes
```

## Troubleshooting

- **"release_command falló"** → revisa `fly logs --app koko-valuation-api`. Suele ser una migración con conflict. Para revertir la última revisión: `alembic downgrade -1`.
- **"rate limit Vivanuncios"** → bajá `VIVANUNCIOS_RATE_LIMIT_RPS` (default `0.5` req/s). Si seguís bloqueado, esperá ~30min antes de reintentar.
- **"comparables vacío"** → verificá que `make seed` haya corrido y que los scrapers hayan ejecutado al menos un ciclo (`make logs-scrapers`).
- **"FX no actualizado"** → revisá `BANXICO_API_TOKEN`; el scraper de Banxico corre diario y cachea el resultado en Redis.

## Licencia

Propietario — KOKO. Todos los derechos reservados.
