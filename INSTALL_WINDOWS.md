# 🪟 Установка на Windows без Docker - MedTest Platform

Пошаговая инструкция по запуску MedTest Platform на Windows 10/11 без использования Docker.

## Системные требования

- **OS**: Windows 10 (build 17763+) или Windows 11
- **RAM**: Минимум 4 GB, рекомендуется 8 GB
- **Disk**: 10 GB свободного места
- **Права**: Администратор (для установки ПО)

---

## Шаг 1: Установка необходимого ПО

### 1.1 Python 3.11

1. Скачайте установщик: https://www.python.org/downloads/release/python-3118/
2. Запустите `python-3.11.8-amd64.exe`
3. ✅ **Обязательно отметьте**: "Add Python 3.11 to PATH"
4. Нажмите "Install Now"
5. После установки проверьте:

```powershell
python --version
# Должно показать: Python 3.11.x
```

### 1.2 Node.js 20 LTS

1. Скачайте установщик: https://nodejs.org/
2. Запустите `node-v20.11.0-x64.msi`
3. Установите с настройками по умолчанию
4. Проверьте:

```powershell
node --version
# Должно показать: v20.x.x

npm --version
# Должно показать: 10.x.x
```

### 1.3 PostgreSQL 16

1. Скачайте установщик: https://www.postgresql.org/download/windows/
2. Запустите `postgresql-16.x-windows-x64.exe`
3. Настройки установки:
   - Порт: `5432` (по умолчанию)
   - Пароль для суперпользователя (postgres): **запомните его!** (например, `postgres`)
   - Locale: `Russian, Russia` или `Default locale`
4. ✅ Установите все компоненты (PostgreSQL Server, pgAdmin 4, Command Line Tools)
5. Проверьте:

```powershell
# Добавьте в PATH, если не добавлено:
# C:\Program Files\PostgreSQL\16\bin

psql --version
# Должно показать: psql (PostgreSQL) 16.x
```

### 1.4 Redis для Windows

Redis официально не поддерживает Windows, но есть порт от Microsoft:

**Вариант 1: Memurai (рекомендуется)**
1. Скачайте: https://www.memurai.com/get-memurai (бесплатная Developer версия)
2. Установите `Memurai-Developer-v4.0.5.msi`
3. Запустите как сервис автоматически

**Вариант 2: Redis от Microsoft (устаревший, но работает)**
1. Скачайте: https://github.com/microsoftarchive/redis/releases
2. Скачайте `Redis-x64-3.0.504.msi`
3. Установите с настройками по умолчанию
4. Порт: `6379`

Проверка:

```powershell
redis-cli ping
# Должно вернуть: PONG
```

Если команда не найдена, запустите Redis вручную:
```powershell
# Найдите redis-server.exe в Program Files
& "C:\Program Files\Redis\redis-server.exe"
```

### 1.5 Git (если еще не установлен)

1. Скачайте: https://git-scm.com/download/win
2. Установите с настройками по умолчанию
3. Проверьте:

```powershell
git --version
```

---

## Шаг 2: Установка MinIO

MinIO - это хранилище для изображений вопросов и других файлов.

### 2.1 Скачивание MinIO

```powershell
# Создайте директорию для MinIO
New-Item -Path "C:\minio" -ItemType Directory -Force
New-Item -Path "C:\minio\data" -ItemType Directory -Force

# Скачайте MinIO (в PowerShell от администратора)
Invoke-WebRequest -Uri "https://dl.min.io/server/minio/release/windows-amd64/minio.exe" -OutFile "C:\minio\minio.exe"
```

**Или скачайте вручную**: https://dl.min.io/server/minio/release/windows-amd64/minio.exe и поместите в `C:\minio\`

### 2.2 Создание скрипта запуска

Создайте файл `C:\minio\start-minio.bat`:

```batch
@echo off
title MinIO Server
set MINIO_ROOT_USER=minioadmin
set MINIO_ROOT_PASSWORD=minioadmin123
C:\minio\minio.exe server C:\minio\data --console-address ":9001"
```

**Проверка**: Запустите `C:\minio\start-minio.bat` (откроется окно консоли, не закрывайте его)

Откройте браузер: http://localhost:9001
- Login: `minioadmin`
- Password: `minioadmin123`

Пока оставьте окно MinIO открытым.

---

## Шаг 3: Настройка PostgreSQL

### 3.1 Создание базы данных

Откройте PowerShell и выполните:

```powershell
# Подключитесь к PostgreSQL (введите пароль, который задали при установке)
psql -U postgres

# В консоли PostgreSQL (postgres=#) выполните:
```

```sql
CREATE DATABASE medtest_db;
CREATE USER medtest_user WITH PASSWORD 'medtest_password';
GRANT ALL PRIVILEGES ON DATABASE medtest_db TO medtest_user;

-- Подключитесь к новой БД
\c medtest_db

-- PostgreSQL 15+: дайте права на схему
GRANT ALL ON SCHEMA public TO medtest_user;

-- Выход
\q
```

### 3.2 Проверка подключения

```powershell
psql -h localhost -U medtest_user -d medtest_db
# Введите пароль: medtest_password

# Если подключение успешно, выйдите: \q
```

---

## Шаг 4: Подготовка проекта

### 4.1 Клонирование репозитория (если еще не сделано)

```powershell
# Выберите папку для проекта, например:
cd E:\pythonProject

git clone https://github.com/your-org/StudyMedTest.git
cd StudyMedTest
```

### 4.2 Настройка Backend

#### Создание виртуального окружения

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate

# После активации в консоли должно появиться (venv)
```

#### Установка зависимостей

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Если возникают ошибки с `pycocotools`**:
```powershell
pip install pycocotools-windows
```

**Если ошибки с компиляцией** (нужен Visual C++):
```powershell
# Установите Visual C++ Build Tools:
# https://visualstudio.microsoft.com/visual-cpp-build-tools/
# Или установите Visual Studio Community с "Desktop development with C++"
```

#### Создание файла конфигурации

Создайте файл `backend\.env` со следующим содержимым:

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

# Security (ОБЯЗАТЕЛЬНО измените SECRET_KEY!)
SECRET_KEY=zmK8j_P7Yn4QxWvEr2TgNhBc9sDfLpMaXuRe5Oi3Vw1k
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET=medtest
MINIO_USE_SSL=false

# LLM APIs (опционально - нужно для оценки текстовых ответов)
# Получите ключи на https://platform.openai.com/api-keys
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Local LLM (если есть GPU и локальная модель)
LOCAL_LLM_ENABLED=false
LOCAL_LLM_URL=http://localhost:8080

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","http://localhost"]

# Environment
ENVIRONMENT=development
DEBUG=true
```

**Важно**: Сгенерируйте уникальный `SECRET_KEY`:
```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
Скопируйте результат и замените в `.env`

#### Применение миграций БД

```powershell
# Убедитесь, что venv активен (должен быть префикс (venv))
alembic upgrade head
```

Если появились ошибки, проверьте:
- PostgreSQL запущен
- Данные в `.env` верны
- База данных создана

#### Создание администратора

Создайте файл `backend\create_admin.py`:

```python
import asyncio
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select


async def create_admin():
    async with AsyncSessionLocal() as db:
        # Проверяем, есть ли уже админ
        result = await db.execute(
            select(User).where(User.email == 'admin@medtest.local')
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print('⚠️  Admin уже существует!')
            return
        
        admin = User(
            email='admin@medtest.local',
            password_hash=get_password_hash('admin123'),
            full_name='Администратор системы',
            role='admin',
            is_active=True,
            is_verified=True
        )
        db.add(admin)
        await db.commit()
        print('✅ Администратор создан успешно!')
        print('   Email: admin@medtest.local')
        print('   Пароль: admin123')
        print('   ⚠️  ОБЯЗАТЕЛЬНО смените пароль после первого входа!')


if __name__ == '__main__':
    asyncio.run(create_admin())
```

Запустите:
```powershell
python create_admin.py
```

### 4.3 Настройка Frontend

Откройте **новое окно PowerShell** (оставьте backend открытым):

```powershell
cd E:\pythonProject\StudyMedTest\frontend
npm install
```

Создайте файл `frontend\.env`:

```env
VITE_API_URL=http://localhost:8000
```

---

## Шаг 5: Настройка MinIO бакета

Создайте файл `backend\setup_minio.py`:

```python
from minio import Minio
from minio.error import S3Error
import json


def setup_minio():
    """Создание бакета для хранения файлов"""
    client = Minio(
        "localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin123",
        secure=False
    )
    
    bucket_name = "medtest"
    
    try:
        # Создание бакета
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            print(f"✅ Бакет '{bucket_name}' создан")
        else:
            print(f"⚠️  Бакет '{bucket_name}' уже существует")
        
        # Публичная политика (для разработки)
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
        
        client.set_bucket_policy(bucket_name, json.dumps(policy))
        print(f"✅ Политика доступа установлена")
        
    except S3Error as e:
        print(f"❌ Ошибка: {e}")


if __name__ == '__main__':
    setup_minio()
```

Запустите (убедитесь, что MinIO запущен):
```powershell
cd backend
.\venv\Scripts\activate
python setup_minio.py
```

---

## Шаг 6: Запуск приложения

Вам понадобится **4 окна PowerShell** (или используйте Windows Terminal с вкладками).

### Окно 1: MinIO (если еще не запущен)

```powershell
C:\minio\start-minio.bat
```

Оставьте окно открытым. Проверка: http://localhost:9001

### Окно 2: Backend API

```powershell
cd E:\pythonProject\StudyMedTest\backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Оставьте окно открытым. Проверка: http://localhost:8000/docs

### Окно 3: Celery Worker

```powershell
cd E:\pythonProject\StudyMedTest\backend
.\venv\Scripts\activate
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo
```

**Важно**: На Windows используйте `--pool=solo`

**Альтернатива** (если `solo` не работает):
```powershell
pip install gevent
celery -A app.tasks.celery_app worker --loglevel=info --pool=gevent
```

Оставьте окно открытым.

### Окно 4: Frontend

```powershell
cd E:\pythonProject\StudyMedTest\frontend
npm run dev
```

Оставьте окно открытым. Откроется браузер или перейдите: http://localhost:5173

---

## Шаг 7: Вход в систему

Откройте браузер: **http://localhost:5173**

**Данные для входа:**
- Email: `admin@medtest.local`
- Пароль: `admin123`

✅ Готово! Система запущена.

---

## Автоматизация запуска

### Создание bat-файла для запуска всех сервисов

Создайте файл `E:\pythonProject\StudyMedTest\start-all.bat`:

```batch
@echo off
title MedTest Platform - Запуск всех сервисов
color 0A

echo ========================================
echo   MedTest Platform - Автозапуск
echo ========================================
echo.

:: Проверка запуска MinIO
echo [1/4] Запуск MinIO...
start "MinIO Server" /MIN cmd /k "C:\minio\start-minio.bat"
timeout /t 3 /nobreak >nul

:: Запуск Backend
echo [2/4] Запуск Backend API...
start "Backend API" cmd /k "cd /d E:\pythonProject\StudyMedTest\backend && .\venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 5 /nobreak >nul

:: Запуск Celery
echo [3/4] Запуск Celery Worker...
start "Celery Worker" cmd /k "cd /d E:\pythonProject\StudyMedTest\backend && .\venv\Scripts\activate && celery -A app.tasks.celery_app worker --loglevel=info --pool=solo"
timeout /t 3 /nobreak >nul

:: Запуск Frontend
echo [4/4] Запуск Frontend...
start "Frontend Dev Server" cmd /k "cd /d E:\pythonProject\StudyMedTest\frontend && npm run dev"

echo.
echo ========================================
echo   Все сервисы запущены!
echo ========================================
echo.
echo   Frontend:  http://localhost:5173
echo   Backend:   http://localhost:8000/docs
echo   MinIO:     http://localhost:9001
echo.
echo   Логин: admin@medtest.local
echo   Пароль: admin123
echo.
echo   Для остановки закройте все окна или
echo   нажмите Ctrl+C в каждом окне.
echo.
pause
```

**Использование:**
1. Дважды кликните `start-all.bat`
2. Откроются 4 окна с сервисами
3. Подождите ~15 секунд
4. Откройте http://localhost:5173

### Создание ярлыка на рабочем столе

1. Правой кнопкой на рабочем столе → Создать → Ярлык
2. Укажите путь: `E:\pythonProject\StudyMedTest\start-all.bat`
3. Имя: `MedTest Platform`
4. Готово!

---

## Остановка приложения

### Способ 1: Ручная остановка
В каждом окне PowerShell нажмите `Ctrl+C`

### Способ 2: Через диспетчер задач
1. `Ctrl+Shift+Esc`
2. Найдите процессы: `python.exe`, `node.exe`, `minio.exe`
3. Завершите их

### Способ 3: Создайте stop-all.bat

Создайте `E:\pythonProject\StudyMedTest\stop-all.bat`:

```batch
@echo off
echo Остановка всех сервисов MedTest...

taskkill /F /FI "WINDOWTITLE eq MinIO*" /T
taskkill /F /FI "WINDOWTITLE eq Backend*" /T
taskkill /F /FI "WINDOWTITLE eq Celery*" /T
taskkill /F /FI "WINDOWTITLE eq Frontend*" /T

echo Все сервисы остановлены.
pause
```

---

## Проверка работы сервисов

### Проверка PostgreSQL

```powershell
# Проверка сервиса
Get-Service -Name postgresql*

# Проверка подключения
psql -U medtest_user -d medtest_db -c "SELECT version();"
```

### Проверка Redis

```powershell
redis-cli ping
# Должно вернуть: PONG
```

Если Redis не отвечает:
```powershell
# Найдите и запустите redis-server.exe
& "C:\Program Files\Redis\redis-server.exe"
```

### Проверка MinIO

```powershell
# PowerShell
Invoke-WebRequest -Uri "http://localhost:9000/minio/health/live" -Method GET
```

### Проверка Backend

```powershell
curl http://localhost:8000/docs
# Или откройте в браузере
```

---

## Решение типичных проблем

### ❌ "Python не найден"

```powershell
# Проверьте установку
python --version

# Если не работает, добавьте в PATH:
# 1. Win+R → sysdm.cpl → Дополнительно → Переменные среды
# 2. В "Системные переменные" найдите Path → Изменить
# 3. Добавьте: C:\Users\ВашеИмя\AppData\Local\Programs\Python\Python311
# 4. Добавьте: C:\Users\ВашеИмя\AppData\Local\Programs\Python\Python311\Scripts
```

### ❌ "Не удается подключиться к PostgreSQL"

```powershell
# Проверьте статус сервиса
Get-Service -Name postgresql*

# Если остановлен, запустите:
Start-Service -Name postgresql-x64-16

# Проверьте, слушает ли порт
netstat -ano | findstr :5432
```

### ❌ "Redis connection refused"

```powershell
# Проверьте, запущен ли Redis
Get-Service -Name Redis

# Если не установлен как сервис, запустите вручную:
& "C:\Program Files\Redis\redis-server.exe"

# Для Memurai:
Get-Service -Name Memurai
Start-Service -Name Memurai
```

### ❌ "MinIO недоступен"

```powershell
# Проверьте процесс
Get-Process minio -ErrorAction SilentlyContinue

# Если не запущен:
C:\minio\start-minio.bat

# Проверьте порты
netstat -ano | findstr :9000
netstat -ano | findstr :9001
```

### ❌ "Module not found" в Backend

```powershell
cd backend
.\venv\Scripts\activate
pip install -r requirements.txt --force-reinstall
```

### ❌ "npm ERR!" в Frontend

```powershell
cd frontend
# Удалите node_modules и переустановите
Remove-Item -Recurse -Force node_modules
Remove-Item -Force package-lock.json
npm install
```

### ❌ Backend запускается, но API не отвечает

Проверьте `.env`:
```powershell
cd backend
cat .env

# Убедитесь, что:
# - DATABASE_URL правильный
# - REDIS_URL правильный
# - SECRET_KEY не пустой
```

### ❌ Frontend не подключается к Backend

Проверьте `frontend\.env`:
```env
VITE_API_URL=http://localhost:8000
```

Проверьте CORS в `backend\.env`:
```env
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000","http://localhost"]
```

### ❌ Ошибка компиляции pycocotools

```powershell
# Установите Visual C++ Build Tools
# https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Или используйте предкомпилированную версию
pip uninstall pycocotools
pip install pycocotools-windows
```

### ❌ Celery не работает на Windows

```powershell
# Используйте --pool=solo
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo

# Или установите gevent
pip install gevent
celery -A app.tasks.celery_app worker --loglevel=info --pool=gevent
```

---

## Полезные команды

```powershell
# Просмотр логов Backend
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --log-level debug

# Запуск тестов Backend
cd backend
.\venv\Scripts\activate
pytest -v

# Запуск тестов Frontend
cd frontend
npm test

# Создание новой миграции БД
cd backend
.\venv\Scripts\activate
alembic revision --autogenerate -m "Описание изменений"
alembic upgrade head

# Откат миграции
alembic downgrade -1

# Просмотр статуса Celery задач
cd backend
.\venv\Scripts\activate
celery -A app.tasks.celery_app inspect active

# Линтинг и форматирование Backend
cd backend
.\venv\Scripts\activate
black .
isort .
flake8 .

# Линтинг Frontend
cd frontend
npm run lint
npm run lint:fix
npm run format
```

---

## Автозапуск при старте Windows (опционально)

### Вариант 1: Через планировщик задач

1. Нажмите `Win+R` → введите `taskschd.msc`
2. Создать задачу → Общие:
   - Имя: `MedTest Platform`
   - ✅ Выполнить с наивысшими правами
3. Триггеры → Создать:
   - Начать задачу: При входе в систему
4. Действия → Создать:
   - Программа: `E:\pythonProject\StudyMedTest\start-all.bat`
5. ОК

### Вариант 2: Через автозагрузку

1. Нажмите `Win+R` → введите `shell:startup`
2. Скопируйте ярлык на `start-all.bat` в эту папку

---

## Production рекомендации для Windows Server

Для продакшена на Windows Server рекомендуется:

1. **Использовать Windows Services** для автозапуска:
   - NSSM (Non-Sucking Service Manager): https://nssm.cc/

```powershell
# Установка Backend как сервиса
nssm install MedTestBackend "E:\pythonProject\StudyMedTest\backend\venv\Scripts\python.exe"
nssm set MedTestBackend AppParameters "-m uvicorn app.main:app --host 0.0.0.0 --port 8000"
nssm set MedTestBackend AppDirectory "E:\pythonProject\StudyMedTest\backend"
nssm start MedTestBackend
```

2. **Использовать IIS** как reverse proxy для Frontend
3. **Настроить SSL** сертификаты
4. **Настроить Windows Backup** для PostgreSQL и MinIO
5. **Настроить Windows Firewall** правила

---

## Дополнительная информация

- [README.md](README.md) - Общая информация
- [QUICKSTART.md](QUICKSTART.md) - Быстрый старт с Docker
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Архитектура
- [docs/API.md](docs/API.md) - API документация

---

## Поддержка

При возникновении проблем:

1. Проверьте, что все сервисы запущены
2. Проверьте логи в окнах PowerShell
3. Проверьте порты: `netstat -ano | findstr "8000 5432 6379 9000"`
4. Создайте issue в GitHub репозитории

---

**Успешного запуска! 🚀**


