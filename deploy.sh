#!/bin/bash

# Скрипт автоматического деплоя с учетом версионности

# 1. Получаем текущий SHA коммита (короткий)
export APP_REVISION=$(git rev-parse --short HEAD)

# 2. Получаем версию из тегов Git, если их нет — используем базовую 0.7.0
# Если тегов нет вообще, git describe выдаст ошибку, поэтому используем fallback
export APP_VERSION=$(git describe --tags --always 2>/dev/null || echo "0.7.0")

echo "=========================================="
echo "🚀 Starting Deployment: $APP_VERSION"
echo "🔧 Revision: $APP_REVISION"
echo "=========================================="

# 3. Синхронизируем изменения
# git pull # Раскомментируйте на сервере

# 4. Сборка и запуск образов
# Мы передаем переменные APP_VERSION и APP_REVISION в docker-compose
docker-compose -f deployment/docker-compose.yml build
docker-compose -f deployment/docker-compose.yml up -d

echo "=========================================="
echo "✅ Deployment complete!"
echo "📡 Health check: http://localhost:8000/health"
echo "=========================================="
