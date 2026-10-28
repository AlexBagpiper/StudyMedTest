#!/bin/bash
# Полный снимок прода для «холодного» архива (HDD / offline).
# Запуск на VPS от medtest, из корня репозитория или deployment/.
#
#   ./deployment/scripts/backup_prod.sh
#   ./deployment/scripts/backup_prod.sh --keep 14
#
# Результат: ~/backups/cold-staging/prod-YYYY-MM-DD_HHMM/
#   + symlink ~/backups/cold-staging/latest
#
# Cron (ежедневно 03:30):
#   30 3 * * * /home/medtest/StudyMedTest/deployment/scripts/backup_prod.sh --keep 7 >> /home/medtest/backups/backup.log 2>&1

set -euo pipefail

KEEP=7
for arg in "$@"; do
  case "$arg" in
    --keep=*) KEEP="${arg#*=}" ;;
    --keep) shift; KEEP="${1:?--keep requires number}" ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO="$(cd "$DEPLOY/.." && pwd)"
cd "$DEPLOY"

_env_get() {
  grep -E "^${1}=" .env | head -1 | cut -d= -f2- | tr -d '\r'
}

POSTGRES_USER="$(_env_get POSTGRES_USER)"
POSTGRES_DB="$(_env_get POSTGRES_DB)"
VERSION="$(_env_get VERSION)"
DOMAIN_NAME="$(_env_get DOMAIN_NAME)"
MINIO_BUCKET="$(_env_get MINIO_BUCKET)"

if [[ -z "$POSTGRES_USER" || -z "$POSTGRES_DB" ]]; then
  echo "ERROR: POSTGRES_USER / POSTGRES_DB missing in deployment/.env"
  exit 1
fi

STAMP="$(date +%Y-%m-%d_%H%M)"
OUT_ROOT="${BACKUP_ROOT:-/home/medtest/backups}/cold-staging"
OUT="$OUT_ROOT/prod-$STAMP"
mkdir -p "$OUT"

echo "== MedTest backup $STAMP =="
echo "output: $OUT"

# --- Postgres: полный логический дамп БД (все таблицы, данные, схема) ---
echo "postgres: database ${POSTGRES_DB}..."
docker compose exec -T db pg_dump \
  -U "${POSTGRES_USER}" \
  -d "${POSTGRES_DB}" \
  -Fc --no-owner --no-acl \
  > "$OUT/medtest_db.dump"

if ! [[ -s "$OUT/medtest_db.dump" ]]; then
  echo "ERROR: medtest_db.dump is empty"
  exit 1
fi

echo "postgres: verify dump..."
if ! docker compose exec -T db pg_restore --list < "$OUT/medtest_db.dump" >/dev/null; then
  echo "ERROR: medtest_db.dump failed pg_restore --list"
  exit 1
fi

echo "postgres: globals (roles)..."
docker compose exec -T db pg_dumpall \
  -U "${POSTGRES_USER}" \
  --globals-only \
  > "$OUT/postgres_globals.sql"

# --- Named volumes (read-only tar) ---
backup_volume() {
  local suffix=$1
  local archive=$2
  local vol
  vol="$(docker volume ls -q --filter "name=${suffix}" | head -1)"
  if [[ -z "$vol" ]]; then
    echo "WARN: volume *${suffix}* not found, skip $archive"
    return 0
  fi
  echo "$archive ($vol)..."
  docker run --rm \
    -v "${vol}:/data:ro" \
    -v "${OUT}:/backup" \
    alpine:3.20 \
    tar -czf "/backup/${archive}" -C /data .
}

backup_volume minio_data minio_data.tar.gz
backup_volume redis_data redis_data.tar.gz

# --- Bind mounts (mox, nginx) — через Docker: root в контейнере читает каталоги от mox/nginx ---
backup_bind_dir() {
  local src=$1
  local archive=$2
  local name=$3
  if [[ ! -d "$src" ]]; then
    echo "WARN: $src missing, skip $archive"
    return 0
  fi
  echo "$archive ($name)..."
  docker run --rm \
    -v "${src}:/data:ro" \
    -v "${OUT}:/backup" \
    alpine:3.20 \
    tar -czf "/backup/${archive}" -C /data .
}

backup_bind_dir "$DEPLOY/mox-data" mox-data.tar.gz "mox mail"
backup_bind_dir "$DEPLOY/nginx/certs" nginx_certs.tar.gz "nginx certs"
backup_bind_dir "$DEPLOY/nginx/templates" nginx_templates.tar.gz "nginx templates"

# --- Secrets (только offline; не коммитить) ---
cp .env "$OUT/.env"
chmod 600 "$OUT/.env"

# --- Manifest ---
GIT_REV="$(git -C "$REPO" rev-parse --short HEAD 2>/dev/null || echo unknown)"
{
  echo "created_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "hostname=$(hostname)"
  echo "git_rev=$GIT_REV"
  echo "version=${VERSION:-unknown}"
  echo "domain=${DOMAIN_NAME:-}"
  echo "postgres_db=${POSTGRES_DB}"
  echo "postgres_user=${POSTGRES_USER}"
  echo "minio_bucket=${MINIO_BUCKET:-}"
  echo "components=medtest_db.dump,postgres_globals.sql,minio_data.tar.gz,redis_data.tar.gz,mox-data.tar.gz,nginx_certs.tar.gz,nginx_templates.tar.gz,.env"
} > "$OUT/MANIFEST.txt"

(
  cd "$OUT"
  sha256sum medtest_db.dump postgres_globals.sql *.tar.gz .env MANIFEST.txt 2>/dev/null || true
) > "$OUT/SHA256SUMS.txt"

ln -sfn "$OUT" "$OUT_ROOT/latest"

# --- Retention on VPS (staging before pull to HDD) ---
if [[ "$KEEP" =~ ^[0-9]+$ ]] && [[ "$KEEP" -gt 0 ]]; then
  mapfile -t OLD < <(ls -1dt "$OUT_ROOT"/prod-* 2>/dev/null | tail -n +"$((KEEP + 1))" || true)
  for dir in "${OLD[@]:-}"; do
    [[ -d "$dir" ]] || continue
    echo "prune $dir"
    rm -rf "$dir"
  done
fi

du -sh "$OUT"
echo "OK: $OUT"
echo "Pull to cold storage: rsync/scp $OUT_ROOT/latest/"
