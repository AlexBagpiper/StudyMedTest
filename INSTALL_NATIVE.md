# 🔧 Установка без Docker - MedTest Platform

Инструкция по запуску MedTest Platform напрямую на хосте без использования Docker.

> 💡 **Только Windows?** Используйте упрощенную инструкцию: [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md)

## Системные требования

- **OS**: Windows 10/11, Linux (Ubuntu 20.04+, Debian 11+), macOS 12+
- **RAM**: Минимум 4 GB, рекомендуется 8 GB
- **Disk**: 10 GB свободного места
- **Python**: 3.11 или выше
- **Node.js**: 18.x или выше
- **PostgreSQL**: 14+ (рекомендуется 16)
- **Redis**: 6+ (рекомендуется 7)

---

## Шаг 1: Установка системных зависимостей

### Windows

```powershell
# Установите Chocolatey (если еще не установлен)
# Запустите PowerShell от имени администратора:
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Установка зависимостей
choco install -y python --version=3.11.7
choco install -y nodejs-lts --version=20.11.0
choco install -y postgresql16 --params '/Password:postgres'
choco install -y redis-64
choco install -y git

# Перезапустите PowerShell после установки
```

**Альтернатива**: Установите вручную:
- Python: https://www.python.org/downloads/
- Node.js: https://nodejs.org/
- PostgreSQL: https://www.postgresql.org/download/windows/
- Redis: https://github.com/microsoftarchive/redis/releases (или используйте WSL)

### Linux (Ubuntu/Debian)

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Python 3.11+
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Node.js 20.x
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# PostgreSQL 16
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update
sudo apt install -y postgresql-16 postgresql-client-16

# Redis 7
sudo apt install -y redis-server

# Дополнительные библиотеки для OpenCV
sudo apt install -y libgl1-mesa-glx libglib2.0-0

# Git
sudo apt install -y git

# Запуск сервисов
sudo systemctl enable postgresql
sudo systemctl start postgresql
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### macOS

```bash
# Установите Homebrew (если еще не установлен)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Установка зависимостей
brew install python@3.11
brew install node@20
brew install postgresql@16
brew install redis
brew install git

# Запуск сервисов
brew services start postgresql@16
brew services start redis
```

---

## Шаг 2: Установка MinIO

MinIO используется для хранения файлов (изображения вопросов, результаты).

### Windows

```powershell
# Скачайте MinIO
curl https://dl.min.io/server/minio/release/windows-amd64/minio.exe -o C:\minio\minio.exe

# Создайте директорию для данных
New-Item -Path "C:\minio\data" -ItemType Directory -Force

# Создайте bat-файл для запуска (C:\minio\start-minio.bat)
@echo off
set MINIO_ROOT_USER=minioadmin
set MINIO_ROOT_PASSWORD=minioadmin123
C:\minio\minio.exe server C:\minio\data --console-address ":9001"
```

Запуск MinIO:
```powershell
C:\minio\start-minio.bat
```

### Linux/macOS

```bash
# Скачайте MinIO
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
sudo mv minio /usr/local/bin/

# Создайте директорию для данных
sudo mkdir -p /data/minio
sudo chown $USER:$USER /data/minio

# Создайте systemd service (опционально)
sudo tee /etc/systemd/system/minio.service > /dev/null <<EOF
[Unit]
Description=MinIO
After=network.target

[Service]
Type=simple
User=$USER
Environment="MINIO_ROOT_USER=minioadmin"
Environment="MINIO_ROOT_PASSWORD=minioadmin123"
ExecStart=/usr/local/bin/minio server /data/minio --console-address ":9001"
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Запуск MinIO
sudo systemctl daemon-reload
sudo systemctl enable minio
sudo systemctl start minio
```

**Или запустите вручную:**
```bash
MINIO_ROOT_USER=minioadmin MINIO_ROOT_PASSWORD=minioadmin123 \
  minio server /data/minio --console-address ":9001"
```

---

## Шаг 3: Настройка PostgreSQL

### Создание базы данных и пользователя

```bash
# Подключитесь к PostgreSQL
# Windows: psql -U postgres
# Linux: sudo -u postgres psql

# В консоли PostgreSQL выполните:
CREATE DATABASE medtest_db;
CREATE USER medtest_user WITH PASSWORD 'medtest_password';
GRANT ALL PRIVILEGES ON DATABASE medtest_db TO medtest_user;

# PostgreSQL 15+: дополнительные права
\c medtest_db
GRANT ALL ON SCHEMA public TO medtest_user;

\q
```

### Проверка подключения

```bash
psql -h localhost -U medtest_user -d medtest_db
# Введите пароль: medtest_password
```

---

## Шаг 4: Настройка Backend

### 4.1 Клонирование репозитория (если еще не сделано)

```bash
git clone https://github.com/your-org/StudyMedTest.git
cd StudyMedTest
```

### 4.2 Создание виртуального окружения

```bash
# Windows
cd backend
python -m venv venv
.\venv\Scripts\activate

# Linux/macOS
cd backend
python3.11 -m venv venv
source venv/bin/activate
```

### 4.3 Установка зависимостей

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Примечание**: Если возникают проблемы с `pycocotools` на Windows:
```bash
pip install pycocotools-windows
```

### 4.4 Создание файла `.env`

Создайте файл `backend/.env`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://medtest_user:medtest_password@localhost:5432/medtest_db
POSTGRES_DB=medtest_db
POSTGRES_USER=medtest_user
POSTGRES_PASSWORD=medtest_password

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# MinIO S3
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET=medtest
MINIO_USE_SSL=false

# LLM APIs (опционально - для оценки текстовых ответов)
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Local LLM (опционально)
LOCAL_LLM_ENABLED=false
LOCAL_LLM_URL=http://localhost:8080

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173", "http://localhost"]

# Environment
ENVIRONMENT=development
DEBUG=true
```

**Важно**: Замените `SECRET_KEY` на случайную строку длиной минимум 32 символа!

Генерация ключа:
```bash
# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# PowerShell
-join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | % {[char]$_})
```

### 4.5 Применение миграций

```bash
# Убедитесь, что виртуальное окружение активно
alembic upgrade head
```

### 4.6 Создание администратора

```bash
# Способ 1: Через Python скрипт
python -c "
import asyncio
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash

async def create_admin():
    async with AsyncSessionLocal() as db:
        admin = User(
            email='admin@medtest.local',
            password_hash=get_password_hash('admin123'),
            full_name='System Administrator',
            role='admin',
            is_active=True,
            is_verified=True
        )
        db.add(admin)
        await db.commit()
        print('✅ Admin created: admin@medtest.local / admin123')

asyncio.run(create_admin())
"
```

**Способ 2**: Создайте файл `backend/create_admin.py`:

```python
import asyncio
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash

async def create_admin():
    async with AsyncSessionLocal() as db:
        # Проверяем, существует ли админ
        from sqlalchemy import select
        result = await db.execute(
            select(User).where(User.email == 'admin@medtest.local')
        )
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin:
            print('⚠️  Admin already exists')
            return
        
        admin = User(
            email='admin@medtest.local',
            password_hash=get_password_hash('admin123'),
            full_name='System Administrator',
            role='admin',
            is_active=True,
            is_verified=True
        )
        db.add(admin)
        await db.commit()
        print('✅ Admin created successfully!')
        print('   Email: admin@medtest.local')
        print('   Password: admin123')

if __name__ == '__main__':
    asyncio.run(create_admin())
```

Запуск:
```bash
python create_admin.py
```

---

## Шаг 5: Настройка Frontend

### 5.1 Установка зависимостей

```bash
cd ../frontend
npm install
```

### 5.2 Создание файла `.env`

Создайте файл `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
```

---

## Шаг 6: Запуск приложения

Вам понадобится **4-5 терминалов** (или используйте tmux/screen/Windows Terminal с вкладками).

### Терминал 1: Backend API

```bash
cd backend
# Активируйте venv, если не активен
# Windows: .\venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Проверка: http://localhost:8000/docs

### Терминал 2: Celery Worker

```bash
cd backend
# Активируйте venv

# Windows
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo

# Linux/macOS
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4
```

**Примечание**: На Windows используйте `--pool=solo` или установите `gevent`:
```bash
pip install gevent
celery -A app.tasks.celery_app worker --loglevel=info --pool=gevent
```

### Терминал 3: Frontend

```bash
cd frontend
npm run dev
```

Проверка: http://localhost:5173 (или порт, указанный Vite)

### Терминал 4: MinIO (если не запущен как сервис)

```bash
# Windows
C:\minio\start-minio.bat

# Linux/macOS
MINIO_ROOT_USER=minioadmin MINIO_ROOT_PASSWORD=minioadmin123 \
  minio server /data/minio --console-address ":9001"
```

Проверка:
- API: http://localhost:9000
- Console: http://localhost:9001 (minioadmin / minioadmin123)

### Терминал 5 (опционально): Celery Flower - мониторинг задач

```bash
cd backend
# Активируйте venv
celery -A app.tasks.celery_app flower --port=5555
```

Проверка: http://localhost:5555

---

## Шаг 7: Создание MinIO бакета

После запуска MinIO создайте бакет для хранения файлов:

### Через консоль MinIO
1. Откройте http://localhost:9001
2. Войдите (minioadmin / minioadmin123)
3. Создайте бакет с именем `medtest`
4. Установите политику доступа: **Public** (или настройте по необходимости)

### Через Python скрипт

Создайте файл `backend/setup_minio.py`:

```python
from minio import Minio
from minio.error import S3Error

def setup_minio():
    client = Minio(
        "localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin123",
        secure=False
    )
    
    bucket_name = "medtest"
    
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            print(f"✅ Bucket '{bucket_name}' created successfully")
        else:
            print(f"⚠️  Bucket '{bucket_name}' already exists")
            
        # Установка публичной политики (для разработки)
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
                }
            ]
        }
        
        import json
        client.set_bucket_policy(bucket_name, json.dumps(policy))
        print(f"✅ Public policy set for bucket '{bucket_name}'")
        
    except S3Error as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    setup_minio()
```

Запуск:
```bash
cd backend
# Активируйте venv
python setup_minio.py
```

---

## Шаг 8: Доступ к приложению

После запуска всех сервисов:

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001
- **Celery Flower**: http://localhost:5555

**Вход в систему:**
- Email: `admin@medtest.local`
- Password: `admin123`

---

## Автоматизация запуска

### Windows: Создайте `start-all.bat`

```batch
@echo off
echo Starting MedTest Platform...

:: Start MinIO
start "MinIO" C:\minio\start-minio.bat

:: Start Backend
start "Backend" cmd /k "cd backend && .\venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

:: Start Celery
timeout /t 5
start "Celery" cmd /k "cd backend && .\venv\Scripts\activate && celery -A app.tasks.celery_app worker --loglevel=info --pool=solo"

:: Start Frontend
timeout /t 5
start "Frontend" cmd /k "cd frontend && npm run dev"

echo All services started!
echo Check: http://localhost:5173
pause
```

### Linux/macOS: Создайте `start-all.sh`

```bash
#!/bin/bash

# Start MinIO
MINIO_ROOT_USER=minioadmin MINIO_ROOT_PASSWORD=minioadmin123 \
  minio server /data/minio --console-address ":9001" &

# Start Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
cd ..

# Start Celery
cd backend
source venv/bin/activate
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4 &
cd ..

# Start Frontend
cd frontend
npm run dev &
cd ..

echo "All services started!"
echo "Frontend: http://localhost:5173"
echo "Backend API: http://localhost:8000/docs"
```

Сделайте исполняемым:
```bash
chmod +x start-all.sh
./start-all.sh
```

### Использование tmux (Linux/macOS)

```bash
#!/bin/bash
# start-tmux.sh

SESSION="medtest"

# Создание сессии
tmux new-session -d -s $SESSION

# Backend
tmux rename-window -t $SESSION:0 'backend'
tmux send-keys -t $SESSION:0 'cd backend && source venv/bin/activate && uvicorn app.main:app --reload' C-m

# Celery
tmux new-window -t $SESSION:1 -n 'celery'
tmux send-keys -t $SESSION:1 'cd backend && source venv/bin/activate && celery -A app.tasks.celery_app worker --loglevel=info' C-m

# Frontend
tmux new-window -t $SESSION:2 -n 'frontend'
tmux send-keys -t $SESSION:2 'cd frontend && npm run dev' C-m

# MinIO
tmux new-window -t $SESSION:3 -n 'minio'
tmux send-keys -t $SESSION:3 'MINIO_ROOT_USER=minioadmin MINIO_ROOT_PASSWORD=minioadmin123 minio server /data/minio --console-address ":9001"' C-m

# Attach к сессии
tmux attach-session -t $SESSION
```

Использование:
```bash
chmod +x start-tmux.sh
./start-tmux.sh

# Переключение между окнами: Ctrl+B -> 0,1,2,3
# Выход из tmux: Ctrl+B -> d (detach)
# Вернуться: tmux attach -t medtest
# Завершить все: tmux kill-session -t medtest
```

---

## Остановка приложения

### Ручная остановка
- В каждом терминале: `Ctrl+C`

### PostgreSQL и Redis (если запущены как сервисы)

**Windows:**
```powershell
Stop-Service -Name postgresql-x64-16
Stop-Service -Name redis
```

**Linux:**
```bash
sudo systemctl stop postgresql
sudo systemctl stop redis-server
sudo systemctl stop minio
```

**macOS:**
```bash
brew services stop postgresql@16
brew services stop redis
```

---

## Troubleshooting

### Backend не запускается

```bash
# Проверьте подключение к БД
psql -h localhost -U medtest_user -d medtest_db

# Проверьте Redis
redis-cli ping

# Проверьте логи
cd backend
uvicorn app.main:app --log-level debug
```

### Celery не работает

```bash
# Проверьте подключение к Redis
redis-cli
> SELECT 1
> KEYS *

# Проверьте Celery с debug логами
celery -A app.tasks.celery_app worker --loglevel=debug
```

### MinIO недоступен

```bash
# Проверьте, запущен ли MinIO
curl http://localhost:9000/minio/health/live

# Проверьте порты
# Windows: netstat -ano | findstr "9000"
# Linux: netstat -tlnp | grep 9000
```

### Frontend не подключается к Backend

Проверьте `frontend/.env`:
```env
VITE_API_URL=http://localhost:8000
```

Проверьте CORS в `backend/.env`:
```env
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173", "http://localhost"]
```

### Проблемы с зависимостями Python на Windows

```bash
# Установите Visual C++ Build Tools
# https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Или установите предкомпилированные пакеты:
pip install --upgrade pip wheel
pip install pipwin
pipwin install opencv-python
pipwin install pycocotools
```

---

## Production рекомендации

Для продакшена рекомендуется:

1. **Использовать systemd (Linux) или Windows Services** для автозапуска
2. **Настроить Nginx** в качестве reverse proxy
3. **Использовать Gunicorn** вместо uvicorn напрямую:
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```
4. **Настроить SSL/TLS** сертификаты
5. **Использовать PostgreSQL репликацию**
6. **Настроить бэкапы БД и MinIO**
7. **Настроить мониторинг** (Prometheus, Grafana)

См. [DEPLOYMENT.md](docs/DEPLOYMENT.md) для детальных инструкций.

---

## Полезные команды

```bash
# Проверка статуса сервисов
# PostgreSQL
psql -U medtest_user -d medtest_db -c "SELECT version();"

# Redis
redis-cli ping

# MinIO
curl http://localhost:9000/minio/health/live

# Тесты Backend
cd backend
pytest

# Тесты Frontend
cd frontend
npm test

# Линтинг Backend
cd backend
black .
isort .
flake8

# Линтинг Frontend
cd frontend
npm run lint:fix
npm run format

# Создание миграции БД
cd backend
alembic revision --autogenerate -m "Description"
alembic upgrade head

# Откат миграции
alembic downgrade -1
```

---

## Дополнительная информация

- [README.md](README.md) - Общая информация о проекте
- [QUICKSTART.md](QUICKSTART.md) - Быстрый старт с Docker
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Архитектура системы
- [docs/API.md](docs/API.md) - API документация
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - Production deployment

---

**Успешного запуска! 🚀**
