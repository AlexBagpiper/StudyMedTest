# MedTest Platform

Современная веб-платформа для тестирования студентов медицинского института с поддержкой текстовых и графических вопросов, LLM-оценкой ответов и Computer Vision для анализа аннотаций.

## Возможности

### Типы вопросов
- **Текстовые вопросы**: Открытые ответы с оценкой по критериям через LLM
- **Графические вопросы**: Аннотирование изображений тканей/препаратов с автоматической оценкой через CV алгоритмы (COCO format)

### Роли пользователей
- **Администратор**: Управление пользователями, доступ ко всем тестам, расширенная аналитика
- **Преподаватель**: Создание вопросов и тестов, просмотр результатов, аналитика
- **Студент**: Прохождение тестов, просмотр результатов

### Технологии

#### Backend
- Python 3.11+
- FastAPI
- SQLAlchemy 2.0 + Alembic
- PostgreSQL 16
- Redis 7
- Celery
- LangChain (LLM интеграция)
- OpenCV, pycocotools (Computer Vision)

#### Frontend
- React 18 + TypeScript
- Material-UI (MUI) v5
- Fabric.js (графический редактор аннотаций)
- React Query + Axios
- Zustand (state management)
- Recharts (аналитика)

#### Infrastructure
- Docker + Docker Compose
- MinIO (S3-compatible storage)
- Nginx (reverse proxy + load balancer)
- Prometheus + Grafana (мониторинг)

## Быстрый старт

> 💡 **Альтернатива**: Если вы предпочитаете установку без Docker:
> - **Windows**: [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md) (упрощенная инструкция)
> - **Все ОС**: [INSTALL_NATIVE.md](INSTALL_NATIVE.md) (полная инструкция)

### Предварительные требования

- Docker 24.0+
- Docker Compose 2.20+
- Git
- (Опционально) NVIDIA GPU + nvidia-docker для локальных LLM

### Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd StudyMedTest
```

2. Создайте `.env` файл:
```bash
cp .env.example .env
# Отредактируйте .env с вашими настройками
```

3. Запустите инфраструктуру:
```bash
docker-compose up -d
```

4. Примените миграции базы данных:
```bash
docker-compose exec backend alembic upgrade head
```

5. Создайте суперпользователя:
```bash
docker-compose exec backend python -m app.cli create-admin
```

6. Откройте браузер:
- Frontend: http://localhost
- Backend API Docs: http://localhost:8000/docs
- MinIO Console: http://localhost:9001

## Разработка

### Backend

Для разработки и тестов используйте отдельный venv с зависимостями из `requirements-dev.txt` (на сервере — только `requirements.txt`, dev-зависимости там конфликтуют).

**Одной командой из корня проекта:**
```bash
python scripts/setup_dev_venv.py
```

Либо вручную:
```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: .\venv\Scripts\activate
pip install -r requirements-dev.txt   # включает requirements.txt + pytest, black, bandit и т.д.
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm start
```

### Запуск тестов

Скрипты `run_tests.py` и `runner.py` сами используют `backend/venv`, если он есть (после `setup_dev_venv.py`).

```bash
# Все тесты (backend venv + frontend)
python scripts/run_tests.py

# Backend вручную
cd backend
.\venv\Scripts\activate   # или source venv/bin/activate
pytest

# Frontend
cd frontend
npm test
```

## Документация

- 📖 **[Полное руководство пользователя (Wiki)](docs/wiki/Home.md)** — Основной источник документации для всех ролей.
- [Архитектура системы](docs/ARCHITECTURE.md)
- [Workflow разработки и деплоя](docs/DEVELOPMENT_WORKFLOW.md) — local-native dev + remote Docker deploy через `./deploy.sh`
- [Регистрация и верификация email](docs/REGISTRATION.md) — флоу, OTP-политика, runbook, threat-model
- [Методология оценки и веса](docs/wiki/ScoringMethodology.md) (Актуально)
- [Технические детали функций](docs/FEATURES_TECHNICAL.md)
- [API Documentation](docs/API.md)
- [Руководство по деплою](docs/DEPLOYMENT.md)

## Лицензия

Proprietary - Все права защищены

