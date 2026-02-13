import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import Role
from app.models.test import Test, TestStatus, TestQuestion
from app.models.question import Question, QuestionType

@pytest.mark.asyncio
async def test_teacher_can_duplicate_admin_test(
    client: AsyncClient,
    db: AsyncSession,
    test_admin: "User",
    test_teacher: "User",
    auth_headers_teacher: dict,
):
    # 1. Admin creates a question and a test
    question = Question(
        author_id=test_admin.id,
        type=QuestionType.TEXT,
        content="Admin Question",
        difficulty=3
    )
    db.add(question)
    await db.flush()

    test = Test(
        author_id=test_admin.id,
        title="Admin Test",
        status=TestStatus.PUBLISHED,
        settings={"time_limit": 45}
    )
    db.add(test)
    await db.flush()

    tq = TestQuestion(test_id=test.id, question_id=question.id, order=0)
    db.add(tq)
    await db.commit()

    # 2. Teacher duplicates the test
    response = await client.post(
        f"/api/v1/tests/{test.id}/duplicate",
        headers=auth_headers_teacher
    )
    assert response.status_code == 200
    data = response.json()
    
    assert data["title"] == "Admin Test (копия)"
    assert data["author_id"] == str(test_teacher.id)
    assert data["status"] == TestStatus.DRAFT
    assert data["settings"]["time_limit"] == 45
    assert len(data["test_questions"]) == 1
    assert data["test_questions"][0]["question_id"] == str(question.id)

    # 3. Teacher can now edit their copy
    response = await client.put(
        f"/api/v1/tests/{data['id']}",
        headers=auth_headers_teacher,
        json={"title": "My Own Test"}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "My Own Test"
