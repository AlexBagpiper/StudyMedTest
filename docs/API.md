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
  "last_name": "Иванов",
  "first_name": "Иван",
  "middle_name": "Иванович",
  "role": "student"
}
```

**Response: 201 Created**
```json
{
  "id": "uuid",
  "email": "student@example.com",
  "last_name": "Иванов",
  "first_name": "Иван",
  "middle_name": "Иванович",
  "role": "student",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### POST /auth/login

Вход в систему.

**Request:**
```http
Content-Type: application/x-form-urlencoded

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
  "last_name": "Иванов",
  "first_name": "Иван",
  "middle_name": "Иванович",
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
  "difficulty": 3,
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
  "difficulty": 3,
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
    "content": "Опишите анатомическое строение...",
    "difficulty": 3,
    "topic_id": "uuid",
    "created_at": "..."
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
    "passing_score": 60.0
  },
  "structure": [
    {
      "topic_id": "uuid",
      "question_type": "text",
      "count": 5,
      "difficulty": 3
    }
  ],
  "questions": [
    {
      "question_id": "uuid",
      "order": 1
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

## Submissions

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
    "total_score": 73,
    "max_score": 100,
    "percentage": 73,
    "grade": "4",
    "weighted_details": {
      "total_weighted": 182,
      "max_weighted": 250
    }
  },
  "answers": [
    {
      "id": "uuid",
      "question_id": "uuid",
      "score": 85,
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

## Interactive Documentation

FastAPI автоматически генерирует интерактивную документацию:

- Swagger UI: `http://your-domain/api/v1/docs` (в зависимости от настроек)
- ReDoc: `http://your-domain/api/v1/redoc`
