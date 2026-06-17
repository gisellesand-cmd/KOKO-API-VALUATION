#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------------------------
# migrate.sh
# ------------------------------------------------------------------------------
# Purpose: Run Alembic migrations for the KOKO MLS Property Valuation API.
# Invoked by Fly.io release_command before promoting new machines.
# Idempotent: re-running with an already-up-to-date DB is a no-op.
# ------------------------------------------------------------------------------

ts() {
  date -u --iso-8601=seconds 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ
}

log() {
  echo "[$(ts)] $*"
}

# --- Validate environment -----------------------------------------------------
if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "[$(ts)] ERROR: DATABASE_URL is not set. Cannot run migrations." >&2
  exit 1
fi

START_TS=$(date -u +%s)
log "Starting Alembic migration run."

# --- Show current revision (don't fail if no revision exists yet) -------------
log "Current Alembic revision (before upgrade):"
if ! alembic current 2>&1; then
  log "WARN: could not read current revision (this is expected on a fresh DB)."
fi

# --- Run upgrade --------------------------------------------------------------
log "Running: alembic upgrade head"
alembic upgrade head

# --- Show new revision --------------------------------------------------------
log "Current Alembic revision (after upgrade):"
alembic current

END_TS=$(date -u +%s)
ELAPSED=$(( END_TS - START_TS ))
log "Migrations completed successfully in ${ELAPSED}s."
