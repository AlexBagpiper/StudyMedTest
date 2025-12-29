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

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm start
```

### Запуск тестов

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

## Архитектура

См. [документацию по архитектуре](docs/architecture.md) для детального описания системы.

## Лицензия

Proprietary - Все права защищены

