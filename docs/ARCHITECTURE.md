# Architecture Documentation - MedTest Platform

## Обзор системы

MedTest Platform — это веб-платформа для тестирования студентов медицинских институтов с поддержкой:
- Текстовых вопросов с LLM-оценкой
- Графических вопросов с аннотациями (Computer Vision)
- Многоуровневой системой доступа (RBAC)
- Асинхронной обработкой через Celery

## Архитектурная схема

```
┌─────────────────────────────────────────────────────┐
│                   Client (Browser)                  │
│           React 18 + TypeScript + MUI              │
└──────────────────┬──────────────────────────────────┘
                   │ REST API (HTTPS)
                   ▼
┌─────────────────────────────────────────────────────┐
│              Nginx (Load Balancer)                  │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌──────────────┐      ┌──────────────┐
│   Backend    │      │   Backend    │
│  Instance 1  │      │  Instance 2  │
│  (FastAPI)   │      │  (FastAPI)   │
└──────┬───────┘      └──────┬───────┘
       │                     │
       └──────────┬──────────┘
                  │
        ┌─────────┴─────────────────┬──────────────────┐
        ▼                           ▼                  ▼
┌──────────────┐          ┌──────────────┐    ┌──────────────┐
│  PostgreSQL  │          │    Redis     │    │    MinIO     │
│     (БД)     │          │   (Cache +   │    │  (Storage)   │
│              │          │    Queue)    │    │              │
└──────────────┘          └──────┬───────┘    └──────────────┘
                                 │
                      ┌──────────┴──────────┐
                      ▼                     ▼
              ┌──────────────┐      ┌──────────────┐
              │Celery Worker │      │Celery Worker │
              │  (LLM/CV)    │      │  (LLM/CV)    │
              └──────────────┘      └──────────────┘
                      │
                      ▼
              ┌──────────────┐
              │  LLM Service │
              │ (OpenAI/     │
              │  Local)      │
              └──────────────┘
```

## Компоненты системы

### 1. Frontend (React + TypeScript)

**Структура:**
```
frontend/
├── src/
│   ├── components/       # Переиспользуемые компоненты
│   │   └── AnnotationEditor.tsx  # Редактор аннотаций (Fabric.js)
│   ├── contexts/         # React contexts
│   │   └── AuthContext.tsx
│   ├── layouts/          # Layouts
│   │   ├── MainLayout.tsx
│   │   └── AuthLayout.tsx
│   ├── pages/            # Страницы
│   │   ├── auth/
│   │   ├── tests/
│   │   ├── questions/
│   │   └── submissions/
│   ├── lib/              # Утилиты
│   │   └── api.ts        # Axios client
│   └── theme.ts          # MUI theme
```

**Ключевые технологии:**
- **React 18**: Функциональные компоненты + hooks
- **TypeScript**: Строгая типизация
- **Material-UI v5**: UI компоненты
- **React Query**: Асинхронное состояние и кэширование
- **Zustand**: State management
- **Fabric.js**: Canvas для аннотаций
- **React Router v6**: Маршрутизация

### 2. Backend (FastAPI + Python 3.11)

**Модульная структура:**
```
backend/
├── app/
│   ├── api/v1/          # API endpoints
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── questions.py
│   │   ├── tests.py
│   │   ├── submissions.py
│   │   └── analytics.py
│   ├── core/            # Конфигурация и утилиты
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── security.py
│   │   └── storage.py
│   ├── models/          # SQLAlchemy ORM
│   ├── schemas/         # Pydantic валидация
│   ├── services/        # Бизнес-логика
│   │   ├── llm_service.py
│   │   └── cv_service.py
│   └── tasks/           # Celery tasks
│       └── evaluation_tasks.py
```

**Ключевые принципы:**
- **Dependency Injection**: через FastAPI Depends
- **Async/Await**: асинхронные операции с БД
- **Type Hints**: полная типизация Python 3.11+
- **Pydantic V2**: валидация и сериализация
- **SQLAlchemy 2.0**: ORM с async support

### 3. База данных (PostgreSQL 16)

**ER-диаграмма:**

```
User (id, email, role, ...)
  ├─── 1:N → Question (автор)
  ├─── 1:N → Test (автор)
  └─── 1:N → Submission (студент)

Question (id, type, content, reference_data, ...)
  ├─── N:1 → ImageAsset (изображение)
  └─── N:M → Test (через TestQuestion)

Test (id, title, settings, status, ...)
  ├─── 1:N → TestQuestion (вопросы)
  └─── 1:N → TestVariant (варианты)

TestVariant (id, question_order, ...)
  └─── 1:N → Submission

Submission (id, status, result, ...)
  └─── 1:N → Answer

Answer (id, student_answer, evaluation, score, ...)
  └─── N:1 → Question
```

**Индексы:**
- `users.email` (UNIQUE)
- `submissions(student_id, test_id, submitted_at DESC)`
- `answers(submission_id, question_id)`
- `questions.content` (GIN full-text search)

### 4. Асинхронная обработка (Celery)

**Очереди:**
- `default`: Общие задачи, orchestration
- `llm`: LLM evaluation (приоритет CPU/Memory)
- `cv`: Computer Vision (приоритет CPU/Memory)

**Задачи:**
```python
evaluate_submission(submission_id)
  ├─ evaluate_text_answer(answer_id)      # Очередь: llm
  └─ evaluate_annotation_answer(answer_id) # Очередь: cv
```

**Мониторинг:**
- Flower dashboard: `http://localhost:5555`
- Prometheus metrics экспортируются

### 5. LLM подсистема

**Абстрактная архитектура:**
```python
LLMRouter
  ├─ OpenAIProvider (GPT-4)
  ├─ ClaudeProvider (Claude 2)
  └─ LocalLLMProvider (LLaMA 70B / Mistral)

Стратегия выбора:
  - critical задачи → OpenAI
  - normal задачи → Local LLM
  - fallback: Local → Cloud
```

**Промпты:**
- Structured output через JSON mode
- Few-shot примеры
- Chain-of-thought reasoning
- Кэширование через Redis (hash запроса)

### 6. Computer Vision модуль

**Алгоритмы:**
```python
CVService.evaluate_annotation():
  1. COCO → Shapely Polygon
  2. Hungarian matching (student ↔ reference)
  3. IoU calculation для каждой пары
  4. Metrics:
     - Accuracy (mean IoU)
     - Completeness (recall)
     - Precision
  5. Weighted score: 50% + 30% + 20%
```

**Библиотеки:**
- `pycocotools`: COCO parsing
- `shapely`: Геометрические операции
- `opencv-python`: Обработка изображений
- `numpy`: Векторизация

### 7. Хранилище (MinIO)

**Структура buckets:**
```
medtest-storage/
├── images/                  # Изображения вопросов
│   └── <uuid>.jpg
├── annotations/             # Эталонные аннотации
│   └── <uuid>.json
└── submissions/             # Аннотации студентов
    └── <submission_id>/
        └── <answer_id>.json
```

**Presigned URLs:**
- Генерация временных URL для доступа к файлам
- Expiration: 1 час
- Автоматическое обновление через API

## Паттерны проектирования

### Repository Pattern
- `models/` — сущности
- Прямое взаимодействие через SQLAlchemy session

### Service Layer
- `services/` — бизнес-логика
- Независимость от API и БД деталей

### Dependency Injection
```python
async def get_current_user(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
) -> User:
    ...
```

### Strategy Pattern (LLM)
```python
class BaseLLMProvider(ABC):
    @abstractmethod
    async def evaluate_answer(...) -> EvaluationResult

class OpenAIProvider(BaseLLMProvider):
    ...
```

## Безопасность

### Authentication
- JWT tokens (Access + Refresh)
- bcrypt password hashing (cost 12)
- Rate limiting (5 login attempts)

### Authorization (RBAC)
```python
PERMISSIONS = {
    "admin": ["*"],
    "teacher": ["question:create", "test:publish", ...],
    "student": ["test:submit", "result:read_own"]
}
```

### Data Protection
- HTTPS (TLS 1.3)
- Database encryption at rest
- PII pseudonymization в логах
- CORS configuration
- CSP headers

### Audit Trail
- Все критичные действия логируются
- Таблица `audit_logs`
- Хранение IP, user agent, timestamp

## Масштабируемость

### Горизонтальное масштабирование
- **Backend**: Stateless, можно добавлять инстансы
- **Celery Workers**: Динамическое масштабирование
- **PostgreSQL**: Read replicas для аналитики

### Кэширование
- **Redis**: Сессии, LLM результаты, метаданные
- **HTTP Cache**: Nginx caching для статики
- **React Query**: Client-side кэширование

### Оптимизация БД
- Connection pooling (10 connections)
- Prepared statements
- Batch inserts
- Index optimization

## Мониторинг и логирование

### Metrics (Prometheus)
```python
llm_requests_total
llm_latency_seconds
submission_processing_time
api_request_duration_seconds
```

### Logging
- Structured logging (JSON)
- Log levels: DEBUG, INFO, WARNING, ERROR
- Rotation: 10MB per file, 3 files

### Alerting
- Backend down > 1 min
- LLM latency > 30s (p95)
- Queue size > 1000 tasks
- Disk usage > 80%

## Производительность

### Benchmarks (целевые)
- API response time: < 200ms (p95)
- LLM evaluation: < 10s per answer
- CV evaluation: < 5s per annotation
- Test submission: < 30s total
- Concurrent users: 500+

### Bottlenecks
1. LLM inference (GPU bound)
2. CV processing (CPU bound)
3. Database queries (optimized with indexes)

## Future Improvements

### Микросервисная архитектура
```
API Gateway
  ├─ Auth Service
  ├─ Test Service
  ├─ Evaluation Service (LLM + CV)
  └─ Analytics Service
```

### Real-time features
- WebSocket для live updates
- Реалтайм мониторинг прохождения тестов
- Collaborative editing

### Advanced LLM
- Fine-tuning на медицинских данных
- Multi-modal models (текст + изображения)
- Explainable AI для оценок

### Advanced CV
- Автоматическое предложение аннотаций (AI-assisted)
- 3D реконструкции
- Видео-аннотации

