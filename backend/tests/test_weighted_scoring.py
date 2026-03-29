import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy import select
from app.models.submission import Submission, SubmissionStatus, Answer
from app.models.question import Question, QuestionType
from app.tasks.evaluation_tasks import evaluate_submission
from app.core.database import AsyncSessionLocal

from app.models.test import Test, TestVariant

@pytest.mark.asyncio
async def test_weighted_submission_scoring(db_session, test_user, test_teacher):
    """
    Проверка корректности взвешенного подсчета баллов на основе сложности вопросов.
    """
    # 0. Создаем тест и вариант
    test_obj = Test(
        id=uuid4(),
        title="Weighted Score Test",
        author_id=test_teacher.id,
        status="published",
        settings={}
    )
    db_session.add(test_obj)
    await db_session.flush()
    
    variant = TestVariant(
        id=uuid4(),
        test_id=test_obj.id,
        variant_code="V1",
        question_order=[]
    )
    db_session.add(variant)
    await db_session.flush()

    # 1. Создаем вопросы с разной сложностью
    # Q1: TEXT, difficulty 1 (Weight 1.0)
    # Q2: TEXT, difficulty 3 (Weight 2.0)
    # Q3: TEXT, difficulty 5 (Weight 3.0)
    
    q1 = Question(
        id=uuid4(),
        author_id=test_teacher.id,
        content="Q1 Easy",
        type=QuestionType.TEXT,
        difficulty=1,
        reference_data={"reference_answer": "Correct"}
    )
    q2 = Question(
        id=uuid4(),
        author_id=test_teacher.id,
        content="Q2 Medium",
        type=QuestionType.TEXT,
        difficulty=3,
        reference_data={"reference_answer": "Correct"}
    )
    q3 = Question(
        id=uuid4(),
        author_id=test_teacher.id,
        content="Q3 Hard",
        type=QuestionType.TEXT,
        difficulty=5,
        reference_data={"reference_answer": "Correct"}
    )
    db_session.add_all([q1, q2, q3])
    await db_session.flush()

    # Связываем вопросы с тестом
    from app.models.test import TestQuestion
    db_session.add_all([
        TestQuestion(test_id=test_obj.id, question_id=q1.id, order=0),
        TestQuestion(test_id=test_obj.id, question_id=q2.id, order=1),
        TestQuestion(test_id=test_obj.id, question_id=q3.id, order=2),
    ])
    variant.question_order = [str(q1.id), str(q2.id), str(q3.id)]
    
    await db_session.commit()

    # 2. Создаем submission и ответы
    submission = Submission(
        id=uuid4(),
        student_id=test_user.id,
        variant_id=variant.id,
        status=SubmissionStatus.IN_PROGRESS,
        started_at=datetime.utcnow()
    )
    db_session.add(submission)
    await db_session.flush()

    # Студент ответил:
    # A1: 100 баллов (100 * 1.0 = 100)
    # A2: 50 баллов  (50 * 2.0 = 100)
    # A3: 0 баллов   (0 * 3.0 = 0)
    # Итого взвешенных: 200
    # Макс взвешенных: 100*1 + 100*2 + 100*3 = 600
    # Процент: 200 / 600 * 100 = 33.33% -> Grade 2
    
    a1 = Answer(submission_id=submission.id, question_id=q1.id, student_answer="Correct", score=100)
    a2 = Answer(submission_id=submission.id, question_id=q2.id, student_answer="Half", score=50)
    a3 = Answer(submission_id=submission.id, question_id=q3.id, student_answer="Wrong", score=0)
    db_session.add_all([a1, a2, a3])
    
    submission.status = SubmissionStatus.EVALUATING
    await db_session.commit()

    # 3. Запускаем оценку (имитируем работу Celery task)
    # Мы вызываем evaluate_submission.run или аналогичный метод, если он есть, 
    # но в нашем файле tasks он просто вызывает run_async(_evaluate())
    # Вызовем напрямую внутреннюю логику или сам таск
    
    from app.tasks.evaluation_tasks import evaluate_submission
    # Т.к. evaluate_submission - это Celery таск, мы можем вызвать его синхронно для теста
    # Но он использует run_async внутри, что может быть проблемой в pytest-asyncio
    # Поэтому мы протестируем саму логику расчета из evaluate_submission
    
    # В тесте мы можем замокать run_evaluate_text_answer, чтобы они не лезли в LLM
    import unittest.mock as mock
    
    # Создаем мок-контекстный менеджер, который не закрывает сессию
    class MockSessionContext:
        def __init__(self, session):
            self.session = session
        async def __aenter__(self):
            return self.session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            # Не закрываем сессию в тесте!
            pass

    # Мокаем DatabaseTask.get_session (который вызывается в evaluate_submission через self.get_session())
    from app.tasks.evaluation_tasks import DatabaseTask
    with mock.patch.object(DatabaseTask, "get_session", return_value=MockSessionContext(db_session)):
        with mock.patch("app.tasks.evaluation_tasks.run_evaluate_text_answer") as mock_eval:
            # Настраиваем мок, чтобы он не менял баллы (мы их уже проставили)
            mock_eval.return_value = {"status": "ok"}
            
            # Вызываем таск напрямую
            result = evaluate_submission(str(submission.id))
        
    # 4. Проверяем результат
    await db_session.refresh(submission)
    assert submission.status == SubmissionStatus.COMPLETED
    assert submission.result["total_score"] == 33
    assert submission.result["grade"] == "2"
    assert submission.result["weighted_details"]["total_weighted"] == 200
    assert submission.result["weighted_details"]["max_weighted"] == 600
