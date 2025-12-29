# API Documentation - MedTest Platform

## Base URL

```
Development: http://localhost:8000/api/v1
Production: https://your-domain.com/api/v1
```

## Authentication

Все защищённые endpoints требуют JWT токен в заголовке:

```http
Authorization: Bearer <access_token>
```

### POST /auth/register

Регистрация нового студента.

**Request:**
```json
{
  "email": "student@example.com",
  "password": "securepassword",
  "full_name": "Иван Иванов",
  "role": "student"
}
```

**Response: 201 Created**
```json
{
  "id": "uuid",
  "email": "student@example.com",
  "full_name": "Иван Иванов",
  "role": "student",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### POST /auth/login

Вход в систему.

**Request:**
```http
Content-Type: application/x-www-form-urlencoded

username=student@example.com&password=securepassword
```

**Response: 200 OK**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

## Users

### GET /users/me

Получение информации о текущем пользователе.

**Response: 200 OK**
```json
{
  "id": "uuid",
  "email": "student@example.com",
  "full_name": "Иван Иванов",
  "role": "student",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-10T12:00:00Z"
}
```

## Questions

### POST /questions

Создание вопроса (teacher, admin).

**Request:**
```json
{
  "type": "text",
  "title": "Строение сердца",
  "content": "Опишите анатомическое строение человеческого сердца",
  "reference_data": {
    "reference_answer": "Сердце состоит из четырёх камер..."
  },
  "scoring_criteria": {
    "factual_correctness": 40,
    "completeness": 30,
    "terminology": 20,
    "structure": 10
  }
}
```

**Response: 201 Created**
```json
{
  "id": "uuid",
  "author_id": "uuid",
  "type": "text",
  "title": "Строение сердца",
  "content": "Опишите анатомическое строение...",
  "reference_data": {...},
  "scoring_criteria": {...},
  "created_at": "2024-01-01T00:00:00Z"
}
```

### GET /questions

Список вопросов.

**Query Parameters:**
- `skip` (int): Offset для пагинации
- `limit` (int): Количество вопросов
- `type` (string): Фильтр по типу (text, image_annotation)

**Response: 200 OK**
```json
[
  {
    "id": "uuid",
    "type": "text",
    "title": "Строение сердца",
    ...
  }
]
```

## Tests

### POST /tests

Создание теста (teacher, admin).

**Request:**
```json
{
  "title": "Анатомия сердечно-сосудистой системы",
  "description": "Тест по модулю 1",
  "settings": {
    "time_limit_minutes": 60,
    "max_attempts": 3,
    "shuffle_questions": true,
    "show_results_immediately": false,
    "passing_score": 60.0
  },
  "questions": [
    {
      "question_id": "uuid",
      "order": 1,
      "weight": 1
    }
  ]
}
```

**Response: 201 Created**
```json
{
  "id": "uuid",
  "author_id": "uuid",
  "title": "Анатомия сердечно-сосудистой системы",
  "status": "draft",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### POST /tests/{test_id}/publish

Публикация теста.

**Response: 200 OK**
```json
{
  "id": "uuid",
  "status": "published",
  "published_at": "2024-01-10T00:00:00Z"
}
```

## Submissions

### POST /submissions

Начать прохождение теста.

**Request:**
```json
{
  "variant_id": "uuid"
}
```

**Response: 201 Created**
```json
{
  "id": "uuid",
  "student_id": "uuid",
  "variant_id": "uuid",
  "status": "in_progress",
  "started_at": "2024-01-10T12:00:00Z"
}
```

### POST /submissions/{id}/answers

Создание/обновление ответа.

**Request (текстовый вопрос):**
```json
{
  "question_id": "uuid",
  "student_answer": "Сердце состоит из четырёх камер: двух предсердий и двух желудочков..."
}
```

**Request (графический вопрос):**
```json
{
  "question_id": "uuid",
  "annotation_data": {
    "images": [...],
    "annotations": [...],
    "categories": [...]
  }
}
```

**Response: 201 Created**
```json
{
  "id": "uuid",
  "submission_id": "uuid",
  "question_id": "uuid",
  "student_answer": "...",
  "score": null,
  "created_at": "2024-01-10T12:05:00Z"
}
```

### POST /submissions/{id}/submit

Отправка теста на проверку.

**Response: 200 OK**
```json
{
  "id": "uuid",
  "status": "evaluating",
  "submitted_at": "2024-01-10T13:00:00Z"
}
```

### GET /submissions/{id}

Получение результатов.

**Response: 200 OK**
```json
{
  "id": "uuid",
  "student_id": "uuid",
  "status": "completed",
  "started_at": "2024-01-10T12:00:00Z",
  "submitted_at": "2024-01-10T13:00:00Z",
  "completed_at": "2024-01-10T13:05:00Z",
  "result": {
    "total_score": 85.5,
    "max_score": 100,
    "percentage": 85.5,
    "grade": "5"
  },
  "answers": [
    {
      "id": "uuid",
      "question_id": "uuid",
      "score": 85.0,
      "evaluation": {
        "criteria_scores": {
          "factual_correctness": 35,
          "completeness": 28,
          "terminology": 18,
          "structure": 9
        },
        "feedback": "Хороший ответ, но можно было бы добавить..."
      }
    }
  ]
}
```

## Analytics

### GET /analytics/teacher

Аналитика для преподавателя.

**Response: 200 OK**
```json
{
  "tests": {
    "total": 15,
    "published": 12,
    "draft": 3
  },
  "questions": {
    "total": 120
  },
  "submissions": {
    "total": 450,
    "completed": 420
  }
}
```

### GET /analytics/admin

Расширенная аналитика для администратора.

**Response: 200 OK**
```json
{
  "users": {
    "total": 250,
    "students": 200,
    "teachers": 48,
    "admins": 2
  },
  "tests": {
    "total": 50,
    "published": 45
  },
  "submissions": {
    "total": 2500,
    "completed": 2400,
    "average_score": 78.5
  }
}
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Validation error message"
}
```

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden
```json
{
  "detail": "Not enough permissions"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Rate Limiting

- Общие endpoints: 60 запросов/минуту
- Auth endpoints: 5 запросов/минуту
- Submissions: 10 запросов/минуту

При превышении лимита возвращается статус `429 Too Many Requests`.

## Interactive Documentation

FastAPI автоматически генерирует интерактивную документацию:

- Swagger UI: `http://your-domain/docs`
- ReDoc: `http://your-domain/redoc`

