# KOKO MLS Property Valuation API — Test Suite

This is the test suite for the KOKO MLS Property Valuation API. It is split into
layers (unit, integration, e2e, load) and enforced by pytest markers and a
coverage gate.

The single most important rule in this codebase is **"Cero datos inventados"**:
the valuation engine never fabricates a number it cannot back with real,
fresh, properly-currencied comparables. A large portion of this test suite
exists to enforce that rule. See "Load-bearing tests" below.

---

## How to run

```bash
# Everything (default: includes coverage report, fails under 85%)
pytest

# Just the fast unit layer (no Docker, no Postgres container)
pytest -m unit

# Skip slow stuff during day-to-day work
pytest -m "not slow"

# Coverage report, html + terminal
pytest --cov

# End-to-end widget tests with a visible browser (debug mode)
pytest tests/e2e --headed
```

Common combos:

```bash
# Run only valuation core tests
pytest tests/test_valuation

# Run a single load-bearing scenario
pytest tests/test_valuation/test_zero_comparables_returns_insufficient.py

# Re-run only failed tests from the last run
pytest --last-failed
```

---

## Test markers

| Marker | Meaning |
| --- | --- |
| `unit` | Fast, fully in-memory. No Postgres, no network, no Docker. |
| `integration` | Requires the Postgres testcontainer (started by `conftest`). |
| `e2e` | Drives a real browser via Playwright. Needs `playwright install` once. |
| `slow` | Long-running tests (large fixtures, broad load shaping). Excluded from CI fast path. |
| `load` | Locust load tests. Run on a schedule, not on every PR. |

Pick markers with `-m "integration and not slow"`, etc.

---

## How to add a new HTML fixture

Scrapers are tested against real HTML snapshots so we can be sure that the
parsers keep working as portals change their markup.

1. Find a representative listing page on inmuebles24 or vivanuncios.
2. Save the rendered HTML to:
   - `tests/fixtures/html/inmuebles24/<slug>.html`
   - or `tests/fixtures/html/vivanuncios/<slug>.html`
3. **Anonymize the file before committing**:
   - Remove the agent's real name, phone, and email.
   - Replace them with `Agent Test`, `+52 000 000 0000`, `agent@example.com`.
   - Strip any tracking IDs that could identify the original listing owner.
4. Reference it from a parametrized test, e.g.:

```python
@pytest.mark.parametrize(
    "fixture_name,expected_price",
    [
        ("tulum-aldea-zama-casa-001", Decimal("8_500_000")),
        ("cancun-zona-hotelera-depto-001", Decimal("12_000_000")),
    ],
)
def test_inmuebles24_parser(fixture_name, expected_price):
    ...
```

Fixtures live under `tests/fixtures/html/` and the `.gitkeep` keeps the
directory present even when empty.

---

## Coverage policy

| Component | Target | Hard floor |
| --- | --- | --- |
| Whole project | ≥ 85 % | 80 % (CI fails under this) |
| Valuation core (`app.valuation.*`) | **≥ 95 %** | 95 % — non-negotiable |
| Scrapers | ≥ 85 % | 80 % |
| API layer | ≥ 85 % | 80 % |

The 85 % global gate is configured in `pyproject.toml`
(`--cov-fail-under=85`). The valuation-core 95 % floor is enforced via a
dedicated `pytest tests/test_valuation --cov=app.valuation --cov-fail-under=95`
job in CI.

If a refactor temporarily dips coverage, you must either restore it in the
same PR or add a justification in the PR body. **Do not lower the gate.**

---

## Load-bearing tests (DO NOT DELETE without product sign-off)

The following tests directly encode the "Cero datos inventados" rule.
Deleting, skipping, or weakening any of them requires sign-off from product
and a documented reason in the PR. They are listed here so reviewers can
spot tampering at a glance:

- `tests/test_valuation/test_zero_comparables_returns_insufficient.py`
- `tests/test_valuation/test_preventas_excluded.py`
- `tests/test_valuation/test_usd_without_exchange_rate_excluded.py`
- `tests/test_valuation/test_usd_with_exchange_rate_converted_correctly.py`
- `tests/test_valuation/test_stale_comparables_excluded.py`
- `tests/test_valuation/test_zone_fallback_to_city_lowers_confidence.py`
- `tests/test_api/test_post_valuation_insufficient_data.py`

These tests are **sacred**. They are the executable spec of the product's
core promise.

---

## The "Cero datos inventados" rule

KOKO does not show estimates it cannot justify. Concretely:

1. **Zero comparables ⇒ no number.** The API returns `confidence: "insuficiente"`
   with all `price_*` fields `null` and a clear `methodology_note` explaining
   why. The widget renders a CTA to talk to a human expert. We never invent
   a placeholder number.
2. **Preventas are excluded.** Listings flagged `is_preventa=True` are
   forward-looking and skew comparables. They are filtered out at the
   query layer, always.
3. **USD without an exchange rate is excluded.** If a comparable is priced
   in USD and we do not have a recent `ExchangeRate` row for `USD_MXN`,
   that comparable is dropped. We never substitute a hard-coded rate.
4. **USD with an exchange rate is converted using the recorded rate** —
   not a hard-coded constant, not yesterday's news, not Banxico-but-we
   forgot-to-store-it. The `ExchangeRate.rate` value is what runs.
5. **Stale comparables are excluded.** Anything with
   `scraped_at < now - 90 days` is dropped. The freshness window is
   enforced at the SQL layer.
6. **Zone fallback lowers confidence.** If we cannot find enough zone-level
   comparables and fall back to city-level, the reported confidence drops
   one level (`alta → media`, `media → baja`, `baja → insuficiente`). The
   widget tells the user the scope used.

Each of those rules has at least one load-bearing test above. They are the
reason this API can be trusted in front of a homeowner who is about to make
the biggest financial decision of their life. **Treat them accordingly.**
