# Architecture Documentation - MedTest Platform

## Обзор системы

MedTest Platform — это веб-платформа для тестирования студентов медицинских институтов с поддержкой:
- Текстовых вопросов с LLM-оценкой.
- Графических вопросов с аннотациями (Computer Vision).
- Многоуровневой системой доступа (RBAC).
- Асинхронной обработкой через Celery.

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
              │ (YandexGPT/  │
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
│   │   └── annotation/   # Редактор аннотаций (Fabric.js)
│   ├── contexts/         # Auth, Locale
│   ├── layouts/          # Main, Auth
│   ├── pages/            # Auth, Tests, Questions, Submissions, Admin
│   ├── lib/              # API client, hooks
│   └── theme.ts          # MUI theme
```

### 2. Backend (FastAPI + Python 3.11)

**Ключевые принципы:**
- **Dependency Injection**: через FastAPI Depends.
- **Async/Await**: асинхронные операции с БД.
- **Pydantic V2**: валидация и сериализация.
- **SQLAlchemy 2.0**: ORM с async support.

### 3. База данных (PostgreSQL 16)

**ER-диаграмма:**

```
User (id, email, role, last_name, first_name, ...)
  ├─── 1:N → Question (автор)
  ├─── 1:N → Test (автор)
  └─── 1:N → Submission (студент)

Question (id, type, content, reference_data, difficulty, topic_id, ...)
  ├─── N:1 → ImageAsset (изображение)
  └─── N:M → Test (через TestQuestion)

Test (id, title, settings, status, ...)
  ├─── 1:N → TestQuestion (вопросы)
  └─── 1:N → TestVariant (варианты)

Submission (id, status, result, ...)
  └─── 1:N → Answer

Answer (id, student_answer, annotation_data, evaluation, score, ...)
  └─── N:1 → Question
```

### 4. Асинхронная обработка (Celery)

**Очереди:**
- `default`: Общие задачи.
- `llm`: Оценка текста (YandexGPT/Local).
- `cv`: Оценка аннотаций (Computer Vision).

### 5. Система оценки (Scoring)

Система использует многоуровневую модель оценки с учетом сложности вопросов.

**Метрики для графических вопросов:**
- Accuracy (50%) — средний IoU (Intersection over Union).
- Completeness (30%) — полнота нахождения объектов.
- Precision (20%) — отсутствие лишних аннотаций.

**Итоговый балл за тест:**
Вычисляется по методу **взвешенной сложности** (Difficulty Weights 1.0–3.0). Итоговый результат нормализуется к 100-балльной шкале и конвертируется в оценку (2–5).

Подробное описание алгоритмов см. в [Системе оценки](SCORING_SYSTEM.md).

### 6. Хранилище (MinIO)

**Структура buckets:**
```
medtest-storage/
├── images/                  # Изображения вопросов
└── submissions/             # Аннотации студентов (в БД JSONB или S3)
```

## Безопасность

### Authorization (RBAC)
```python
PERMISSIONS = {
    "admin": ["*"],
    "teacher": ["question:create", "test:publish", ...],
    "student": ["test:submit", "result:read_own"]
}
```

### Audit Trail
- Таблица `audit_logs` хранит действия администраторов и критические события.
