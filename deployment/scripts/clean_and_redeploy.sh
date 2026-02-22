#!/bin/bash
# Остановка контейнеров, очистка образов приложения и пересборка с нуля.
# Запуск: из корня репо ./deployment/scripts/clean_and_redeploy.sh
#         или из deployment/ ./scripts/clean_and_redeploy.sh

set -e

if [ -f "deployment/docker-compose.yml" ]; then
  ROOT="."
elif [ -f "docker-compose.yml" ]; then
  ROOT=".."
  cd "$ROOT"
else
  echo "Run from repo root or from deployment/."
  exit 1
fi

COMPOSE_CMD="docker compose -f deployment/docker-compose.yml"

echo "Stopping and removing containers..."
$COMPOSE_CMD down

echo "Removing app images to force fresh build..."
docker rmi medtest-backend:latest medtest-frontend:latest 2>/dev/null || true
docker rmi medtest-backend:${APP_VERSION:-latest} medtest-frontend:${APP_VERSION:-latest} 2>/dev/null || true

echo "Building with no cache..."
$COMPOSE_CMD build --no-cache

echo "Starting containers..."
$COMPOSE_CMD up -d

echo "Done. Check: $COMPOSE_CMD ps && $COMPOSE_CMD logs -f"
