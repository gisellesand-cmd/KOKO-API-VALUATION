# Scrapers — KOKO MLS Comparables Pipeline

Pipeline de extracción de anuncios de Inmuebles24 y Vivanuncios para alimentar la tabla `comparables` que usa el API de valuación de KOKO MLS.

**Regla no negociable — "Cero datos inventados":** si un fetch falla, la corrida se marca `failed` en `scrape_runs` y se aborta. Si un comparable está en USD y no hay tipo de cambio Banxico disponible, se descarta — nunca se inventa una tasa. Las preventas se marcan `is_preventa=True` y se excluyen del cálculo de mediana aguas abajo.

## Stack

Python 3.11+, httpx async, selectolax (parser HTML), SQLAlchemy 2.x async + asyncpg.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install 'httpx[http2]' beautifulsoup4 selectolax 'sqlalchemy[asyncio]' asyncpg python-dotenv pytest pytest-asyncio
cp .env.example .env
# llena DATABASE_URL y BANXICO_API_TOKEN
```

## Variables de entorno

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | Postgres async URL, p.ej. `postgresql+asyncpg://user:pass@localhost:5432/koko_mls` |
| `BANXICO_API_TOKEN` | Token de Banxico SIE — registro: https://www.banxico.org.mx/SieAPIRest |
| `LOG_LEVEL` | Opcional, default `INFO` |

## Correr scrapers

### Una corrida puntual

```bash
python -m scrapers.runner --source inmuebles24 --city tulum --pages 5
python -m scrapers.runner --source vivanuncios --city cancun --property-type departamento --pages 3
python -m scrapers.runner --source inmuebles24 --city playa-del-carmen --zone playacar --operation venta --pages 4
```

### Dry-run (sin escribir DB)

```bash
python -m scrapers.runner --source inmuebles24 --city tulum --pages 2 --dry-run
```

### Refrescar tipo de cambio Banxico (FIX serie SF63528)

Correr diariamente — el normalizador descarta listings en USD si no hay tasa.

```bash
python -m scrapers.exchange_rate
```

### Generar plantilla de crontab

```bash
python -m scrapers.cron_config > crontab.txt
crontab crontab.txt   # revisa antes de instalar
```

## Tests

Todos los tests son offline — usan fixtures HTML en `tests/fixtures/`.

```bash
pytest tests/
```

## Rate limits

- **Inmuebles24**: 3s mínimo entre fetches de página (`MIN_DELAY_SECONDS = 3.0`), 30s timeout, retry con backoff exponencial en 5xx/red, 60s sleep en 429.
- **Vivanuncios** (free tier): 1 corrida cada 30 min — enforce in-process vía timestamp a nivel de clase (`MIN_RUN_INTERVAL_SECONDS = 1800`). Para deshabilitar (cuenta pagada): `VivanunciosScraper(bypass_run_throttle=True)`. La plantilla de cron espacia las corridas a ≥2h por ciudad.

## Cero datos inventados — qué se descarta

| Condición | Acción |
|---|---|
| Fetch HTTP falla tras 3 reintentos | `ScrapeError` → corrida marcada `failed`, fila no se crea |
| Card sin `data-id` / `data-adid` | Card omitida, log info |
| Card sin precio o precio no parseable | Card omitida, log info |
| Listing en USD sin tasa Banxico vigente | Comparable descartado, log warning `fx_rate_missing` |
| `is_preventa = True` | Se guarda pero downstream (valuación) lo filtra |

## Troubleshooting

- **403 de Inmuebles24** → el User-Agent rota por instancia; espera, baja `--pages`, o cambia de IP. Si persiste, considera un proxy.
- **429** → el scraper duerme 60s y reintenta una vez. Si vuelve a aparecer, baja la cadencia del cron y aumenta el delay.
- **`no_listings_found` en página 1** → probable bloqueo IP O slug de ciudad/zona mal formado. Abre la URL impresa en el log a mano y verifica.
- **`no_fx_rate_available` warnings** → corre `python -m scrapers.exchange_rate` y asegúrate que el cron de Banxico esté activo.
- **Vivanuncios `rate_limit_window_active`** → espera la ventana de 30 min o instancia con `bypass_run_throttle=True` (solo si tienes plan pagado).
- **`db.session not importable`** → la capa de DB aún no está construida; usa `--dry-run` para validar el parsing.

## Layout

```
scrapers/
  base.py            # BaseScraper, ListingPayload, ScrapeError, helpers compartidos
  inmuebles24.py     # Inmuebles24Scraper
  vivanuncios.py     # VivanunciosScraper (con throttle 30 min)
  normalize.py       # normalize_price_to_mxn, normalize_payload
  exchange_rate.py   # fetcher Banxico FIX (SF63528)
  runner.py          # CLI argparse + upsert + scrape_runs lifecycle
  cron_config.py     # plantilla de crontab
tests/
  fixtures/          # HTML capturado sin datos personales
  test_base.py
  test_inmuebles24_parser.py
  test_vivanuncios_parser.py
```
