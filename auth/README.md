# Auth Module — KOKO MLS Property Valuation API

## Overview

This module (`auth/`) provides API key authentication, tier-based rate
limiting, and a request-context middleware for the KOKO MLS Property
Valuation API. It exposes FastAPI dependencies the `api/` specialist can
import and mount on routes — the auth module itself does NOT modify any
routes.

## Tiers

| Tier   | API key required? | Rate limit  | Typical use                                  |
|--------|-------------------|-------------|----------------------------------------------|
| public | No                | 20 / hour   | KOKO landing-page widget, anonymous quick estimate |
| free   | Yes               | 100 / day   | Individual developers, hobby integrations     |
| paid   | Yes               | 10,000+ / day | Production partners (KOKO landing backend, real estate platforms) |

The KOKO landing-page widget calls the **public** valuation endpoint with
no API key — visitors get one estimate without signup friction. See the
"Decision: tier for the KOKO landing widget" section below.

## Endpoints — public vs authenticated

**Public** (no API key, IP-based rate limit only):
- `/health`, `/docs`, `/openapi.json` — exempt from auth AND rate limiting.
- `/v1/valuations/public` (or similar) — exempt from auth, subject to IP
  rate limit via `Depends(rate_limit())`.

**Authenticated** (require `X-API-Key`):
- `/v1/valuations`, `/v1/batch`, anything else — mount with
  `Depends(require_api_key)` and `Depends(rate_limit())`.

## Creating an API key

```bash
python -m auth.admin create-key --name "KOKO Landing" --tier paid
```

Output prints the plain key **once**. The DB stores only an argon2 hash —
the plain key cannot be recovered later. If lost: revoke and create new.

## Listing & revoking keys

```bash
python -m auth.admin list-keys
python -m auth.admin revoke-key 42
```

`list-keys` shows the key prefix (first 12 chars of the original plain key),
never the full plain. `revoke-key` sets `active=False` and stamps
`revoked_at` — the row stays for audit trail.

## Using a key (client side)

```bash
curl -H "X-API-Key: kmls_aB3xY7sNqRzL..." \
     https://api.koko.example/v1/valuations
```

The header name is `X-API-Key`. Plain key prefix is always `kmls_`.

## Integrating from `api/main.py`

```python
from fastapi import Depends, FastAPI

from auth.dependencies import require_api_key
from auth.middleware import install_middleware
from auth.rate_limit import init_rate_limiter, rate_limit

app = FastAPI()
install_middleware(app)
init_rate_limiter(app)

@app.get("/health")  # exempt from auth and rate limit
def health():
    return {"status": "ok"}

@app.post(
    "/v1/valuations/public",
    dependencies=[Depends(rate_limit())],
)
def public_valuation(...):
    ...  # KOKO landing widget; tier resolves to "public"

@app.post(
    "/v1/valuations",
    dependencies=[Depends(require_api_key), Depends(rate_limit())],
)
def authed_valuation(...):
    ...
```

Do NOT wrap `/health`, `/docs`, or `/openapi.json` with either dependency.

## Configuration

| Env var       | Required | Default       | Purpose                                            |
|---------------|----------|---------------|----------------------------------------------------|
| `REDIS_URL`   | No       | (in-memory)   | Rate-limit storage. Without it, limits are per-process. |
| `DATABASE_URL`| Yes      | —             | Owned by the database specialist; used by `db.session`. |

## Troubleshooting

- **401 "Invalid or revoked API key"** — the supplied key isn't in the DB,
  is inactive, or has `revoked_at` set. Verify with
  `python -m auth.admin list-keys`.
- **401 "Missing API key"** — the endpoint requires `X-API-Key` but the
  header wasn't sent. For public endpoints the header is optional; this
  message should not appear there.
- **429 "Rate limit exceeded"** — caller is over their tier's limit. The
  response includes a `Retry-After` header (seconds). Upgrade tier or wait.
- **Argon2 verification is slow** — expected (~100–500 ms per check). We
  iterate active keys and verify each on lookup; at scale, add a
  deterministic short-lookup-prefix column to `ApiKey` and filter on it
  before verifying.
- **Redis unavailable on startup** — module falls back to in-memory and
  logs a WARNING. Rate limits will NOT be shared across workers in this
  mode; do not run multiple workers without Redis in production.

## Decision: tier for the KOKO landing widget

The landing-page widget calls the public valuation endpoint anonymously
(no API key, no signup). It maps to the **public** tier with an IP-based
rate limit (20 / hour) to balance accessibility against abuse. If abuse
becomes a problem, escalation options are: (a) tighten the per-IP limit,
(b) require CAPTCHA in front of the widget, (c) require email signup to
get a free-tier key. This matches PRD §4 (rate limiting to prevent abuse).

## Security notes

- API keys are hashed with argon2 via passlib; the plain key is never
  logged or stored.
- The plain key is shown exactly once at creation. Recovery is not
  possible; revoke and reissue if lost.
- Revoked keys keep their row (audit trail) with `active=False` and a
  `revoked_at` timestamp.
- The middleware sets `X-Request-ID` on every response — correlate with
  structured logs (`caller`, `tier`, `duration_ms`, `status_code`) when
  investigating issues.
