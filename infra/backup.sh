#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------------------------
# backup.sh
# ------------------------------------------------------------------------------
# Purpose: Weekly pg_dump of the KOKO MLS Property Valuation Postgres DB,
# compressed with gzip and uploaded to S3. Designed to run from a Fly.io
# machine or a GitHub Action.
#
# Required env vars:
#   DATABASE_URL          - Postgres connection string
#   BACKUP_S3_BUCKET      - Target S3 bucket (no s3:// prefix)
#   AWS_ACCESS_KEY_ID     - AWS credentials
#   AWS_SECRET_ACCESS_KEY - AWS credentials
#
# Optional env vars:
#   AWS_REGION            - AWS region (default: us-east-1)
#   BACKUP_RETENTION_DAYS - Prune backups older than N days (default: 90)
# ------------------------------------------------------------------------------

ts() {
  date -u --iso-8601=seconds 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ
}

log() {
  echo "[$(ts)] $*"
}

# --- Validate required env ----------------------------------------------------
MISSING=()
[[ -z "${DATABASE_URL:-}" ]]          && MISSING+=("DATABASE_URL")
[[ -z "${BACKUP_S3_BUCKET:-}" ]]      && MISSING+=("BACKUP_S3_BUCKET")
[[ -z "${AWS_ACCESS_KEY_ID:-}" ]]     && MISSING+=("AWS_ACCESS_KEY_ID")
[[ -z "${AWS_SECRET_ACCESS_KEY:-}" ]] && MISSING+=("AWS_SECRET_ACCESS_KEY")

if (( ${#MISSING[@]} > 0 )); then
  echo "[$(ts)] ERROR: missing required environment variables:" >&2
  for v in "${MISSING[@]}"; do
    echo "  - $v" >&2
  done
  exit 1
fi

export AWS_REGION="${AWS_REGION:-us-east-1}"
export AWS_DEFAULT_REGION="$AWS_REGION"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-90}"

START_TS=$(date -u +%s)
log "Starting Postgres backup. Region=${AWS_REGION} Bucket=${BACKUP_S3_BUCKET}"

# --- Build filename + S3 key --------------------------------------------------
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
YEAR=$(date -u +%Y)
MONTH=$(date -u +%m)
FILENAME="koko-mls-backup-${STAMP}.sql.gz"
LOCAL_PATH="/tmp/${FILENAME}"
S3_KEY="postgres/${YEAR}/${MONTH}/${FILENAME}"
S3_URI="s3://${BACKUP_S3_BUCKET}/${S3_KEY}"

# --- Dump + compress ----------------------------------------------------------
log "Running pg_dump and piping through gzip -> ${LOCAL_PATH}"
# Note: pg_dump's exit status is preserved because pipefail is set.
pg_dump "$DATABASE_URL" \
  --no-owner \
  --no-acl \
  --format=plain \
  --clean \
  --if-exists \
  | gzip -9 > "$LOCAL_PATH"

# --- Verify dump non-empty ----------------------------------------------------
if [[ ! -s "$LOCAL_PATH" ]]; then
  echo "[$(ts)] ERROR: dump file ${LOCAL_PATH} does not exist or is empty." >&2
  rm -f "$LOCAL_PATH"
  exit 1
fi

# Portable file size in bytes (BSD stat on macOS, GNU stat on Linux).
SIZE_BYTES=$(stat -f%z "$LOCAL_PATH" 2>/dev/null || stat -c%s "$LOCAL_PATH")
if (( SIZE_BYTES <= 1024 )); then
  echo "[$(ts)] ERROR: dump file too small (${SIZE_BYTES} bytes <= 1024). Aborting." >&2
  rm -f "$LOCAL_PATH"
  exit 1
fi

SIZE_MB=$(awk -v b="$SIZE_BYTES" 'BEGIN { printf "%.2f", b/1024/1024 }')
log "Dump OK: ${LOCAL_PATH} (${SIZE_BYTES} bytes, ${SIZE_MB} MB)"

# --- Upload to S3 -------------------------------------------------------------
log "Uploading to ${S3_URI} (storage class: STANDARD_IA)..."
aws s3 cp "$LOCAL_PATH" "$S3_URI" \
  --storage-class STANDARD_IA \
  --only-show-errors

log "Upload successful."

# --- Cleanup local file -------------------------------------------------------
rm -f "$LOCAL_PATH"
log "Removed local file ${LOCAL_PATH}."

# --- Prune old backups --------------------------------------------------------
# Delete backups older than BACKUP_RETENTION_DAYS (default 90) from the
# postgres/ prefix. We iterate `aws s3 ls --recursive` and compare each
# object's LastModified date (YYYY-MM-DD) to a cutoff date.
log "Pruning backups older than ${BACKUP_RETENTION_DAYS} days under s3://${BACKUP_S3_BUCKET}/postgres/ ..."

# Compute cutoff date in seconds-since-epoch (portable: GNU date vs BSD date).
if date -u -d "@0" >/dev/null 2>&1; then
  # GNU date
  CUTOFF_EPOCH=$(date -u -d "${BACKUP_RETENTION_DAYS} days ago" +%s)
else
  # BSD date (macOS)
  CUTOFF_EPOCH=$(date -u -v-"${BACKUP_RETENTION_DAYS}"d +%s)
fi

PRUNED=0
# aws s3 ls --recursive output columns: <date> <time> <size> <key>
while read -r line; do
  [[ -z "$line" ]] && continue
  OBJ_DATE=$(awk '{print $1}' <<<"$line")
  OBJ_KEY=$(awk '{for (i=4; i<=NF; i++) printf "%s%s", $i, (i<NF?" ":"")}' <<<"$line")
  [[ -z "$OBJ_DATE" || -z "$OBJ_KEY" ]] && continue

  if date -u -d "@0" >/dev/null 2>&1; then
    OBJ_EPOCH=$(date -u -d "${OBJ_DATE}" +%s 2>/dev/null || echo "")
  else
    OBJ_EPOCH=$(date -u -j -f "%Y-%m-%d" "${OBJ_DATE}" +%s 2>/dev/null || echo "")
  fi
  [[ -z "$OBJ_EPOCH" ]] && continue

  if (( OBJ_EPOCH < CUTOFF_EPOCH )); then
    log "Pruning old backup: s3://${BACKUP_S3_BUCKET}/${OBJ_KEY} (modified ${OBJ_DATE})"
    aws s3 rm "s3://${BACKUP_S3_BUCKET}/${OBJ_KEY}" --only-show-errors || true
    PRUNED=$(( PRUNED + 1 ))
  fi
done < <(aws s3 ls "s3://${BACKUP_S3_BUCKET}/postgres/" --recursive || true)

log "Prune complete. Removed ${PRUNED} object(s)."

# --- Summary ------------------------------------------------------------------
END_TS=$(date -u +%s)
ELAPSED=$(( END_TS - START_TS ))
log "Backup uploaded: ${S3_URI} size: ${SIZE_MB} MB elapsed: ${ELAPSED}s"
