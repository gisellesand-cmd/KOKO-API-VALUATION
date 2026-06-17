# Monitoring

Observability assets for the KOKO MLS Property Valuation API.

## Contents

- `sentry.py` — optional Sentry initialization helper for the FastAPI app.
  Safe to import even when `sentry_sdk` is not installed; `init_sentry()`
  becomes a no-op in that case.
- `grafana-dashboard.json` — Grafana dashboard (schema v38) showing request
  rate, p95 latency, comparables count distribution, and scraper success
  rate, all sourced from Prometheus.

## Enabling Sentry

Sentry is opt-in. It only initializes when `SENTRY_DSN` is set.

1. Install the SDK (already in production requirements):

   ```
   pip install "sentry-sdk[fastapi]"
   ```

2. Set the DSN as a Fly secret on the API app:

   ```
   fly secrets set SENTRY_DSN="https://<key>@oXXXX.ingest.sentry.io/<project>" -a koko-valuation-api
   ```

3. Optional environment variables:

   - `SENTRY_ENVIRONMENT` (defaults to `ENVIRONMENT` env, or `production`)
   - `SENTRY_TRACES_SAMPLE_RATE` (float, default `0.1`)
   - `SENTRY_RELEASE` (defaults to `GIT_SHA` env, or `unknown`)

4. Call `init_sentry()` once at FastAPI app startup:

   ```python
   from monitoring.sentry import init_sentry

   init_sentry()
   app = FastAPI(...)
   ```

If the DSN is missing, the app logs `Sentry disabled (no DSN)` and continues
normally. Any unexpected error during init is swallowed and logged to stderr
so Sentry can never crash the API.

## Importing the Grafana dashboard

1. Open Grafana.
2. Go to **Dashboards > New > Import**.
3. Paste the contents of `grafana-dashboard.json` into the **Import via panel
   json** text area (or upload the file).
4. Select your Prometheus data source when prompted.
5. Click **Import**.

The dashboard's `uid` is `koko-mls-api`; re-importing will update the
existing dashboard rather than creating a duplicate.

## Prometheus scrape config

Add the following job to your Prometheus configuration so it scrapes the
metrics the dashboard expects. The FastAPI app exposes `/metrics` and Fly
publishes the metrics port (9091) over HTTPS:

```yaml
scrape_configs:
  - job_name: koko-valuation-api
    scrape_interval: 15s
    scheme: https
    metrics_path: /metrics
    static_configs:
      - targets:
          - koko-valuation-api.fly.dev:9091
```

After reloading Prometheus, confirm the target is `UP` under
**Status > Targets**, then return to the dashboard to see live data.
