import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import Role
from app.models.question import Question, QuestionType

@pytest.mark.asyncio
async def test_teacher_can_duplicate_admin_question(
    client: AsyncClient,
    db: AsyncSession,
    test_admin: "User",
    test_teacher: "User",
    auth_headers_teacher: dict,
):
    # 1. Admin creates a question
    question = Question(
        author_id=test_admin.id,
        type=QuestionType.IMAGE_ANNOTATION,
        content="Admin Image Question",
        difficulty=4,
        reference_data={"labels": [{"id": "1", "name": "Organ", "color": "#ff0000"}]},
        scoring_criteria={"allow_partial": True}
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)

    # 2. Teacher duplicates the question
    response = await client.post(
        f"/api/v1/questions/{question.id}/duplicate",
        headers=auth_headers_teacher
    )
    assert response.status_code == 200
    data = response.json()
    
    assert data["content"] == "Admin Image Question (копия)"
    assert data["author_id"] == str(test_teacher.id)
    assert data["type"] == QuestionType.IMAGE_ANNOTATION
    assert data["difficulty"] == 4
    assert data["reference_data"]["labels"][0]["name"] == "Organ"
    assert data["scoring_criteria"]["allow_partial"] is True

    # 3. Teacher can now edit their copy
    response = await client.put(
        f"/api/v1/questions/{data['id']}",
        headers=auth_headers_teacher,
        json={"content": "My Own Question"}
    )
    assert response.status_code == 200
    assert response.json()["content"] == "My Own Question"
