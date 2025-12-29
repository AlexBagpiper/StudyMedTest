# Deployment Guide - MedTest Platform

## Предварительные требования

### Минимальные системные требования (On-Premise)

- **Сервер приложений**: 8 CPU cores, 16 GB RAM, 100 GB SSD
- **Сервер БД**: 4 CPU cores, 8 GB RAM, 200 GB SSD (может быть тот же сервер)
- **Сервер storage**: 4 CPU cores, 8 GB RAM, 500 GB+ HDD/SSD
- **GPU сервер (опционально для локальных LLM)**: NVIDIA A100/H100, 32 GB+ VRAM

### Софт

- Docker 24.0+
- Docker Compose 2.20+
- Nginx (если не используется Docker Compose nginx)
- PostgreSQL 16 (если не через Docker)
- Git

## Быстрый старт (Development)

```bash
# 1. Клонирование репозитория
git clone <repository-url>
cd StudyMedTest

# 2. Копирование и настройка переменных окружения
cp .env.example .env
# Отредактируйте .env с вашими настройками

# 3. Запуск всех сервисов
docker-compose up -d

# 4. Применение миграций БД
docker-compose exec backend alembic upgrade head

# 5. Создание первого администратора
docker-compose exec backend python -m app.cli create-admin

# 6. Открытие в браузере
# Frontend: http://localhost
# Backend API: http://localhost:8000/docs
```

## Production Deployment

### 1. Подготовка сервера

```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Проверка установки
docker --version
docker-compose --version
```

### 2. Настройка переменных окружения

Создайте `.env` файл с production настройками:

```env
# Database (используйте сильные пароли!)
POSTGRES_PASSWORD=<strong-random-password>
DATABASE_URL=postgresql://medtest_user:<strong-password>@db:5432/medtest

# Security
SECRET_KEY=<generate-with-openssl-rand-hex-32>

# MinIO
MINIO_ROOT_PASSWORD=<strong-random-password>

# LLM API Keys (если используете облачные)
OPENAI_API_KEY=<your-key>
ANTHROPIC_API_KEY=<your-key>

# Email (для уведомлений)
SMTP_HOST=smtp.your-domain.com
SMTP_USER=noreply@your-domain.com
SMTP_PASSWORD=<smtp-password>

# Monitoring
SENTRY_DSN=<your-sentry-dsn>
ENVIRONMENT=production
```

### 3. SSL сертификаты

```bash
# Используйте Let's Encrypt для бесплатных SSL сертификатов
sudo apt-get install certbot

# Получение сертификата
sudo certbot certonly --standalone -d your-domain.com

# Копирование сертификатов
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/certs/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/certs/

# Раскомментируйте SSL блок в nginx/nginx.conf
```

### 4. Запуск production

```bash
# Сборка и запуск
docker-compose -f docker-compose.yml up -d --build

# Проверка статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 5. Миграции и инициализация

```bash
# Применение миграций
docker-compose exec backend alembic upgrade head

# Создание администратора
docker-compose exec backend python -c "
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash
import asyncio

async def create_admin():
    async with AsyncSessionLocal() as db:
        admin = User(
            email='admin@your-domain.com',
            password_hash=get_password_hash('your-secure-password'),
            full_name='System Administrator',
            role='admin',
            is_active=True,
            is_verified=True
        )
        db.add(admin)
        await db.commit()
        print('Admin created successfully')

asyncio.run(create_admin())
"
```

## Мониторинг

### Prometheus + Grafana

```bash
# Добавьте в docker-compose.yml
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    volumes:
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    ports:
      - "3001:3000"
```

### Логи

```bash
# Просмотр логов в реальном времени
docker-compose logs -f

# Экспорт логов
docker-compose logs > logs_$(date +%Y%m%d).txt

# Ротация логов (настроить в docker-compose.yml)
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

## Бэкапы

### Автоматический бэкап (cron)

```bash
# Создайте скрипт /usr/local/bin/medtest-backup.sh
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/backups/medtest

# PostgreSQL backup
docker-compose exec -T db pg_dump -U medtest_user medtest | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# MinIO backup
docker-compose exec -T minio mc mirror minio/medtest-storage $BACKUP_DIR/minio_$DATE/

# Удаление старых бэкапов (старше 30 дней)
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete
find $BACKUP_DIR -name "minio_*" -mtime +30 -exec rm -rf {} \;

echo "Backup completed: $DATE"
```

```bash
# Добавьте в crontab
sudo crontab -e
# Добавьте строку (бэкап каждый день в 2:00 AM):
0 2 * * * /usr/local/bin/medtest-backup.sh >> /var/log/medtest-backup.log 2>&1
```

## Масштабирование

### Горизонтальное масштабирование backend

```yaml
# В docker-compose.yml увеличьте replicas
  backend:
    ...
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

### Load Balancer (Nginx)

Nginx автоматически распределяет нагрузку между репликами backend.

### Celery Workers

```bash
# Увеличьте количество workers
docker-compose scale celery_worker=4
```

## Обновление системы

```bash
# 1. Создайте бэкап
/usr/local/bin/medtest-backup.sh

# 2. Получите обновления
git pull origin main

# 3. Остановите сервисы
docker-compose down

# 4. Пересоберите образы
docker-compose build

# 5. Запустите обновлённую версию
docker-compose up -d

# 6. Примените новые миграции
docker-compose exec backend alembic upgrade head

# 7. Проверьте работоспособность
docker-compose ps
docker-compose logs -f
```

## Troubleshooting

### Backend недоступен

```bash
# Проверка логов
docker-compose logs backend

# Проверка состояния контейнера
docker-compose ps backend

# Перезапуск
docker-compose restart backend
```

### База данных недоступна

```bash
# Проверка подключения
docker-compose exec backend python -c "
from app.core.database import engine
import asyncio
asyncio.run(engine.connect())
print('DB connection OK')
"

# Восстановление из бэкапа
gunzip < backup.sql.gz | docker-compose exec -T db psql -U medtest_user medtest
```

### Медленная работа LLM

```bash
# Проверка очереди Celery
docker-compose exec backend celery -A app.tasks.celery_app inspect active

# Увеличение количества workers
docker-compose scale celery_worker=6
```

## Безопасность

### Регулярные обновления

```bash
# Обновление образов
docker-compose pull
docker-compose up -d

# Обновление системных пакетов
sudo apt update && sudo apt upgrade -y
```

### Firewall

```bash
# Разрешить только необходимые порты
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### Аудит безопасности

```bash
# Docker security scan
docker scan medtest-backend:latest

# Проверка уязвимостей в зависимостях
docker-compose exec backend pip install safety
docker-compose exec backend safety check
```

## Поддержка

Для получения помощи:
- Документация: `/docs`
- Issues: GitHub Issues
- Email: support@your-domain.com

