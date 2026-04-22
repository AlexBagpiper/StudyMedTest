#!/bin/bash
set -euo pipefail

# Автоматический деплой MedTest Platform.
# Запуск на production-сервере после `git pull`.
#
# Использование:
#   ./deploy.sh                  обычный деплой: pull → build → up -d
#   ./deploy.sh --clean          полная пересборка (down + no-cache build)
#   ./deploy.sh --smoke          + end-to-end smoke-тесты регистрации и email
#   ./deploy.sh --migrate-legacy + конвертировать pending_reg:* -> reg:draft:*
#                                 (сохраняет данные студентов в процессе регистрации;
#                                  они жмут «Отправить код повторно» и получают новый код)
#   ./deploy.sh --cleanup-legacy + удалить legacy-ключи pending_reg:* без миграции
#   ./deploy.sh --rollback       откат на предыдущий git commit
#
# Флаги комбинируются: ./deploy.sh --clean --smoke --migrate-legacy
#
# Требования на сервере:
#   - docker compose v2
#   - deployment/.env (скопирован из deployment/env.example и заполнен)

CLEAN=0
SMOKE=0
ROLLBACK=0
CLEANUP_LEGACY=0
MIGRATE_LEGACY=0
for arg in "$@"; do
  case "$arg" in
    --clean)          CLEAN=1 ;;
    --smoke)          SMOKE=1 ;;
    --rollback)       ROLLBACK=1 ;;
    --cleanup-legacy) CLEANUP_LEGACY=1 ;;
    --migrate-legacy) MIGRATE_LEGACY=1 ;;
    *) echo "Unknown flag: $arg"; exit 2 ;;
  esac
done

if [[ $CLEANUP_LEGACY -eq 1 && $MIGRATE_LEGACY -eq 1 ]]; then
  echo "❌ Используйте --migrate-legacy ИЛИ --cleanup-legacy, но не оба одновременно."
  exit 2
fi

cd "$(dirname "$0")"

COMPOSE="docker compose -f deployment/docker-compose.yml"
REDIS_CONTAINER="medtest-redis"

# --- Rollback: берём предыдущий коммит и делаем обычный деплой.
if [[ $ROLLBACK -eq 1 ]]; then
  echo "⏪ Rolling back to previous commit..."
  git reset --hard HEAD~1
fi

# --- 1. Версия/ревизия.
export APP_REVISION=$(git rev-parse --short HEAD)
export APP_VERSION=$(git describe --tags --always 2>/dev/null || echo "1.0.0")
if [ -f "deployment/.env" ]; then
  VERSION_IN_ENV=$(grep "^VERSION=" deployment/.env | cut -d'=' -f2 || true)
  if [ -n "${VERSION_IN_ENV:-}" ]; then
    export APP_VERSION=$VERSION_IN_ENV
  fi
fi

echo "=========================================="
echo "🚀 Deploy: $APP_VERSION ($APP_REVISION)"
[[ $CLEAN -eq 1 ]]          && echo "🧹 Clean: down + build --no-cache"
[[ $SMOKE -eq 1 ]]          && echo "🔬 Smoke tests enabled"
[[ $MIGRATE_LEGACY -eq 1 ]] && echo "🔄 Migrate legacy pending_reg:* → reg:draft:* (keeps user data)"
[[ $CLEANUP_LEGACY -eq 1 ]] && echo "🗑️  Cleanup legacy Redis keys (pending_reg:*)"
[[ $ROLLBACK -eq 1 ]]       && echo "⏪ Rollback mode"
echo "=========================================="

# --- 2. Актуализация кода (кроме rollback — там уже reset).
if [[ $ROLLBACK -eq 0 ]]; then
  git pull --ff-only
  git fetch --tags
fi

# --- 3. Env-проверки.
if [ ! -f "deployment/.env" ]; then
  if [ -f "deployment/env.example" ]; then
    echo "💡 Creating deployment/.env from env.example..."
    cp deployment/env.example deployment/.env
    echo "❗ PLEASE EDIT deployment/.env AND RUN DEPLOY AGAIN!"
    exit 1
  fi
  echo "❌ deployment/.env missing and no env.example found."
  exit 1
fi

_require_real_secret() {
  local var=$1
  local val
  val=$(grep -E "^${var}=" deployment/.env | head -1 | cut -d'=' -f2- || true)
  if [[ "$val" == "CHANGE_ME"* ]] || [[ "$val" == "generate_a_random_string_here" ]]; then
    echo "❌ deployment/.env: ${var} is still a placeholder. Fix before deploying."
    exit 1
  fi
}
_require_real_secret SECRET_KEY
_require_real_secret SMTP_PASSWORD

# --- 4. Снимок очередей ДО деплоя (на случай если что-то пойдёт не так).
_redis_is_up() {
  docker ps --format '{{.Names}}' | grep -q "^${REDIS_CONTAINER}$"
}

_queue_snapshot() {
  local label=$1
  if ! _redis_is_up; then
    echo "  (Redis container не запущен — снимок пропущен: $label)"
    return 0
  fi
  echo "📦 Redis snapshot ($label):"
  local drafts otps pending_old celery_q email_q rl_keys
  drafts=$(docker exec "$REDIS_CONTAINER" redis-cli -n 0 --scan --pattern "reg:draft:*" | wc -l | tr -d ' ')
  otps=$(docker exec "$REDIS_CONTAINER" redis-cli -n 0 --scan --pattern "reg:otp:*"   | wc -l | tr -d ' ')
  pending_old=$(docker exec "$REDIS_CONTAINER" redis-cli -n 0 --scan --pattern "pending_reg:*" | wc -l | tr -d ' ')
  celery_q=$(docker exec "$REDIS_CONTAINER" redis-cli -n 1 LLEN celery 2>/dev/null || echo "?")
  email_q=$(docker exec "$REDIS_CONTAINER" redis-cli -n 1 LLEN email  2>/dev/null || echo "?")
  rl_keys=$(docker exec "$REDIS_CONTAINER" redis-cli -n 4 --scan | wc -l | tr -d ' ')
  printf "  reg:draft:       %s\n"  "$drafts"
  printf "  reg:otp:         %s\n"  "$otps"
  printf "  pending_reg:*    %s   %s\n" "$pending_old" \
    "$([[ "$pending_old" -gt 0 ]] && echo '(legacy — use --cleanup-legacy to remove)' || echo '')"
  printf "  celery queue:    %s tasks\n" "$celery_q"
  printf "  email  queue:    %s tasks\n" "$email_q"
  printf "  rate-limit keys: %s\n" "$rl_keys"
}

_queue_snapshot "before deploy"

# --- 5. Сборка и запуск.
if [[ $CLEAN -eq 1 ]]; then
  $COMPOSE down
  docker rmi "medtest-backend:${APP_VERSION}" "medtest-frontend:${APP_VERSION}" 2>/dev/null || true
  docker rmi medtest-backend:latest medtest-frontend:latest 2>/dev/null || true
  $COMPOSE build --no-cache
else
  $COMPOSE build
fi

$COMPOSE up -d --remove-orphans --force-recreate

# --- 6. Ожидание готовности и smoke-checks.
echo "⏳ Waiting for services to stabilise (15s)..."
sleep 15

echo ""
echo "📊 Service status:"
$COMPOSE ps

echo ""
echo "🩺 Backend /health:"
if curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
  curl -s http://localhost:8000/health | head -c 200; echo ""
else
  echo "⚠️  Backend /health unreachable. Check: $COMPOSE logs backend --tail=50"
  exit 1
fi

# --- 7. Проверка Celery-воркеров — КАКИЕ ОЧЕРЕДИ они реально слушают.
echo ""
echo "🩺 Celery active queues:"
_check_worker_queues() {
  local service=$1
  local expected_queue=$2
  local output
  if ! output=$($COMPOSE exec -T "$service" celery -A app.tasks.celery_app inspect active_queues 2>&1); then
    echo "  ⚠️  $service: не отвечает"
    return 1
  fi
  if echo "$output" | grep -q "\"name\": \"$expected_queue\""; then
    echo "  ✅ $service: listens on '$expected_queue'"
    return 0
  fi
  echo "  ❌ $service: NOT listening on '$expected_queue'"
  echo "     Раскладка: $(echo "$output" | grep -oE '"name": "[^"]+"' | tr '\n' ' ')"
  return 1
}
_check_worker_queues celery_worker       celery || true
_check_worker_queues celery_email_worker email  || true

# --- 8. Legacy migration / cleanup (опционально).
if [[ $MIGRATE_LEGACY -eq 1 ]]; then
  echo ""
  echo "🔄 Migrating legacy pending_reg:* → reg:draft:* ..."
  # Выполняется внутри уже запущенного backend-контейнера — там есть access к app.*
  $COMPOSE exec -T backend python scripts/dev_diag.py --migrate-legacy || {
    echo "⚠️  Миграция не завершилась успешно. Логи выше."
  }
elif [[ $CLEANUP_LEGACY -eq 1 ]]; then
  echo ""
  echo "🗑️  Cleaning up legacy Redis keys..."
  LEGACY_KEYS=$(docker exec "$REDIS_CONTAINER" redis-cli -n 0 --scan --pattern "pending_reg:*")
  if [ -n "$LEGACY_KEYS" ]; then
    COUNT=$(echo "$LEGACY_KEYS" | wc -l | tr -d ' ')
    echo "$LEGACY_KEYS" | xargs -r docker exec -i "$REDIS_CONTAINER" redis-cli -n 0 DEL >/dev/null
    echo "  deleted $COUNT legacy pending_reg:* keys"
  else
    echo "  (нет legacy-ключей)"
  fi
fi

# --- 9. End-to-end smoke test.
if [[ $SMOKE -eq 1 ]]; then
  echo ""
  echo "🔬 Registration smoke test:"
  SMOKE_EMAIL="smoke_$(date +%s)@example.com"

  RESPONSE=$(curl -sS -X POST http://localhost:8000/api/v1/auth/register \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$SMOKE_EMAIL\",\"password\":\"Smoke123!\",\"last_name\":\"Smoke\",\"first_name\":\"Test\"}")
  echo "  register response: $RESPONSE"
  if ! echo "$RESPONSE" | grep -q "resend_after"; then
    echo "  ❌ Unexpected register response."
    exit 1
  fi

  # Подождём, чтобы email-worker успел забрать задачу.
  sleep 2
  EMAIL_DEPTH_AFTER=$(docker exec "$REDIS_CONTAINER" redis-cli -n 1 LLEN email 2>/dev/null || echo "?")
  echo "  email queue depth AFTER register: $EMAIL_DEPTH_AFTER (ожидается 0 — задачу забрал worker)"

  # Убедиться что OTP реально сохранён.
  OTP_EXISTS=$(docker exec "$REDIS_CONTAINER" redis-cli -n 0 EXISTS "reg:otp:$SMOKE_EMAIL")
  if [ "$OTP_EXISTS" = "1" ]; then
    echo "  ✅ OTP записан в Redis"
  else
    echo "  ❌ OTP NOT found — проверьте backend-логи"
    exit 1
  fi

  # Очищаем за собой.
  docker exec "$REDIS_CONTAINER" redis-cli -n 0 DEL \
    "reg:draft:$SMOKE_EMAIL" "reg:otp:$SMOKE_EMAIL" >/dev/null
  echo "  smoke data cleaned up"
fi

# --- 10. Снимок очередей ПОСЛЕ.
echo ""
_queue_snapshot "after deploy"

echo ""
echo "=========================================="
echo "✅ Deployment complete: $APP_VERSION ($APP_REVISION)"
echo "=========================================="
echo "Logs:     $COMPOSE logs -f backend celery_email_worker"
echo "Health:   curl https://your-domain/health"
echo "Rollback: ./deploy.sh --rollback"
echo "Diag:     docker compose -f deployment/docker-compose.yml exec backend python scripts/dev_diag.py"
