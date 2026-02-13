"""
Практическая проверка CV-оценки графических аннотаций
Тестирование на реальном тесте в БД
"""
import pytest
from uuid import UUID
from datetime import datetime
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.test import Test, TestQuestion, TestStatus, TestVariant
from app.models.question import Question, QuestionType
from app.models.submission import Submission, SubmissionStatus, Answer
from app.models.user import User
from app.services.cv_service import cv_service

@pytest.fixture
async def cv_question(db, test_admin):
    """Создание тестового вопроса с графической аннотацией"""
    # Мы всегда создаем новый вопрос для этого теста, чтобы данные были предсказуемы
    question = Question(
        type=QuestionType.IMAGE_ANNOTATION,
        content="Тестовый графический вопрос",
        reference_data={
            "annotations": [
                {
                    "id": "ref1",
                    "type": "rectangle", 
                    "bbox": [100, 100, 50, 50], 
                    "label_id": "label1"
                }
            ]
        },
        difficulty=1,
        author_id=test_admin.id
    )
    db.add(question)
    await db.flush()
    return question

@pytest.mark.asyncio
async def test_scenario_1_perfect_match(cv_question):
    """Сценарий 1: Идеальное совпадение"""
    student_data = {
        "annotations": cv_question.reference_data.get("annotations", [])
    }
    
    result = await cv_service.evaluate_annotation(
        student_data=student_data,
        reference_data=cv_question.reference_data or {},
        image_id=cv_question.image_id
    )
    
    assert result['total_score'] >= 95

@pytest.mark.asyncio
async def test_scenario_2_partial_match(cv_question):
    """Сценарий 2: Частичное совпадение (смещение)"""
    ref_annotations = cv_question.reference_data.get("annotations", [])
    
    student_annotations = []
    for ann in ref_annotations:
        modified = ann.copy()
        if ann.get('type') == 'rectangle':
            bbox = ann['bbox']
            # Смещение на 40% ширины - это должно существенно снизить балл
            modified['bbox'] = [bbox[0] + bbox[2] * 0.4, bbox[1], bbox[2], bbox[3]]
        elif ann.get('type') == 'polygon':
            points = ann['points'][:]
            # Смещение всех X на 20 пикселей
            modified['points'] = [p + 20 if i % 2 == 0 else p for i, p in enumerate(points)]
        student_annotations.append(modified)
    
    result = await cv_service.evaluate_annotation(
        student_data={"annotations": student_annotations},
        reference_data=cv_question.reference_data or {},
        image_id=cv_question.image_id
    )
    
    # Score должен быть заметно ниже 100
    assert result['total_score'] < 95

@pytest.mark.asyncio
async def test_scenario_5_real_submission(db, cv_question, test_user):
    """Сценарий 5: Полная проверка через БД"""
    # Создаём тестовый Test
    test = Test(
        author_id=(await db.execute(select(User.id).limit(1))).scalar_one(),
        title="CV Test",
        status=TestStatus.PUBLISHED,
        settings={}
    )
    db.add(test)
    await db.flush()
    
    db.add(TestQuestion(test_id=test.id, question_id=cv_question.id, order=1))
    
    variant = TestVariant(
        test_id=test.id, 
        variant_code=f"TEST_CV_{cv_question.id.hex[:6]}", 
        question_order=[str(cv_question.id)]
    )
    db.add(variant)
    await db.flush()
    
    submission = Submission(
        student_id=test_user.id, 
        variant_id=variant.id, 
        status=SubmissionStatus.IN_PROGRESS
    )
    db.add(submission)
    await db.flush()
    
    answer = Answer(
        submission_id=submission.id, 
        question_id=cv_question.id, 
        annotation_data={"annotations": []}
    )
    db.add(answer)
    await db.commit()
    
    await db.refresh(answer)
    assert answer.id is not None
