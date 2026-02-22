#!/bin/bash

# Скрипт автоматического деплоя с учетом версионности
# Использование: ./deploy.sh [--clean]
#   --clean  остановить контейнеры, удалить образы backend/frontend и собрать с нуля

CLEAN=0
[[ " $* " =~ " --clean " ]] && CLEAN=1

# 1. Получаем текущий SHA коммита (короткий)
export APP_REVISION=$(git rev-parse --short HEAD)

# 2. Получаем версию из тегов Git, если их нет — используем базовую 0.7.0
export APP_VERSION=$(git describe --tags --always 2>/dev/null || echo "0.7.0")

echo "=========================================="
echo "🚀 Starting Deployment: $APP_VERSION"
echo "🔧 Revision: $APP_REVISION"
[[ $CLEAN -eq 1 ]] && echo "🧹 Clean redeploy (down → rm images → build --no-cache → up)"
echo "=========================================="

# 3. Синхронизируем изменения
git pull
git fetch --tags

COMPOSE="docker compose -f deployment/docker-compose.yml"

if [[ $CLEAN -eq 1 ]]; then
  $COMPOSE down
  docker rmi medtest-backend:${APP_VERSION} medtest-frontend:${APP_VERSION} 2>/dev/null || true
  docker rmi medtest-backend:latest medtest-frontend:latest 2>/dev/null || true
  $COMPOSE build --no-cache
fi

# 4. Сборка и запуск образов
$COMPOSE build
$COMPOSE up -d

echo "=========================================="
echo "✅ Deployment complete!"
echo "📡 Health check: http://localhost:8000/health"
echo "=========================================="
