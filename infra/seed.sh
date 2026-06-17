#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------------------------
# seed.sh
# ------------------------------------------------------------------------------
# Purpose: Seed reference data for the KOKO MLS Property Valuation API.
#   - Mexico cities (CDMX, Monterrey, Guadalajara, Querétaro, etc.)
#   - Zones within each city
#   - Property types (casa, departamento, terreno, etc.)
#
# Idempotent: the underlying Python seed modules use ON CONFLICT DO NOTHING /
# upserts, so this script is safe to re-run.
# ------------------------------------------------------------------------------

ts() {
  date -u --iso-8601=seconds 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ
}

log() {
  echo "[$(ts)] $*"
}

# --- Validate environment -----------------------------------------------------
if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "[$(ts)] ERROR: DATABASE_URL is not set. Cannot seed data." >&2
  exit 1
fi

START_TS=$(date -u +%s)
log "Starting reference data seed run."

# --- Cities -------------------------------------------------------------------
log "Seeding cities (db.seeds.cities)..."
python -m db.seeds.cities

# --- Zones --------------------------------------------------------------------
log "Seeding zones (db.seeds.zones)..."
python -m db.seeds.zones

# --- Property types -----------------------------------------------------------
log "Seeding property types (db.seeds.property_types)..."
python -m db.seeds.property_types

END_TS=$(date -u +%s)
ELAPSED=$(( END_TS - START_TS ))
log "Seed run completed successfully in ${ELAPSED}s."
log "Row counts are reported by each seed module above."
