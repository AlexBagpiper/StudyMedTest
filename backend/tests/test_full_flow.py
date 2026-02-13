import pytest
from httpx import AsyncClient
from uuid import UUID

@pytest.mark.asyncio
async def test_complete_student_flow(client: AsyncClient, test_teacher, auth_headers_teacher, test_user, auth_headers_student):
    """
    Полный цикл: создание темы -> вопроса -> теста -> прохождение студентом
    """
    # 1. Создание темы (teacher)
    topic_res = await client.post(
        "/api/v1/topics",
        json={"name": "Тестовая тема", "description": "Описание"},
        headers=auth_headers_teacher
    )
    assert topic_res.status_code == 201
    topic_id = topic_res.json()["id"]

    # 2. Создание вопроса (teacher)
    question_res = await client.post(
        "/api/v1/questions",
        json={
            "type": "text",
            "content": "Что такое клетка?",
            "topic_id": topic_id,
            "difficulty": 1,
            "reference_data": {"answer": "Основная единица жизни"},
            "scoring_criteria": {"factual_correctness": 10}
        },
        headers=auth_headers_teacher
    )
    assert question_res.status_code == 201
    question_id = question_res.json()["id"]

    # 3. Создание теста (teacher)
    test_res = await client.post(
        "/api/v1/tests",
        json={
            "title": "Тестовый экзамен",
            "description": "Проверка знаний",
            "settings": {"time_limit": 30},
            "questions": [{"question_id": question_id, "order": 1}]
        },
        headers=auth_headers_teacher
    )
    assert test_res.status_code == 201
    test_id = test_res.json()["id"]

    # 4. Публикация теста (teacher)
    publish_res = await client.post(
        f"/api/v1/tests/{test_id}/publish",
        headers=auth_headers_teacher
    )
    assert publish_res.status_code == 200

    # 5. Начало теста студентом
    start_res = await client.post(
        f"/api/v1/tests/{test_id}/start",
        headers=auth_headers_student
    )
    assert start_res.status_code == 200
    submission_id = start_res.json()["id"]

    # 6. Отправка ответа
    answer_res = await client.post(
        f"/api/v1/submissions/{submission_id}/answers",
        json={
            "question_id": question_id,
            "student_answer": "Это элементарная единица строения всех живых организмов",
            "time_spent": 10
        },
        headers=auth_headers_student
    )
    assert answer_res.status_code == 200

    # 7. Завершение теста
    submit_res = await client.post(
        f"/api/v1/submissions/{submission_id}/submit",
        headers=auth_headers_student
    )
    assert submit_res.status_code == 200
