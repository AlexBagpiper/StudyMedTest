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

## Быстрый старт (Production)

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd StudyMedTest/deployment
```

2. Создайте и настройте `.env`:
```bash
cp env.example .env
# Укажите DOMAIN_NAME и CERTBOT_EMAIL в .env
```

3. Запустите всё одной командой:
```bash
docker compose up -d --build
```
*Система сама получит SSL, применит миграции и создаст админа.*

4. Откройте браузер:
- Frontend: `https://your-domain.com`
- API Docs: `https://your-domain.com/api/docs`
- Webmail: `https://mail.your-domain.com/webmail/`

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

