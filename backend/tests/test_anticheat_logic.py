import pytest
from uuid import uuid4
from datetime import datetime
from sqlalchemy import select
from app.models.submission import Submission, Answer
from app.models.question import Question, QuestionType
from app.models.audit import AuditLog
from app.tasks.evaluation_tasks import run_evaluate_text_answer
import unittest.mock as mock

@pytest.mark.asyncio
async def test_anticheat_event_log_processing(db_session, test_teacher, test_user):
    """
    Проверка сбора данных анти-чита из логов аудита.
    """
    # 0. Создаем тест и вариант (нужны для submission)
    from app.models.test import Test, TestVariant
    test_obj = Test(
        id=uuid4(),
        title="Anticheat Test",
        author_id=test_teacher.id,
        status="published",
        settings={}
    )
    db_session.add(test_obj)
    await db_session.flush()
    
    variant = TestVariant(
        id=uuid4(),
        test_id=test_obj.id,
        variant_code="AV1",
        question_order=[]
    )
    db_session.add(variant)
    await db_session.flush()

    # 1. Подготовка данных
    question_id = uuid4()
    submission_id = uuid4()
    answer_id = uuid4()
    
    question = Question(
        id=question_id,
        author_id=test_teacher.id,
        content="Test Question",
        type=QuestionType.TEXT,
        event_log_check_enabled=True,
        reference_data={}
    )
    submission = Submission(id=submission_id, student_id=test_user.id, variant_id=variant.id)
    answer = Answer(id=answer_id, submission_id=submission_id, question_id=question_id, student_answer="Student Text")
    
    db_session.add_all([question, submission, answer])
    await db_session.flush()

    # 2. Создаем события аудита
    start_time = datetime.utcnow()
    events = [
        # Начало (просто событие для фиксации времени)
        AuditLog(user_id=submission.student_id, action="submission.start", resource_type="submission", resource_id=submission_id, timestamp=start_time),
        # Ушел из вкладки на 10 секунд
        AuditLog(user_id=submission.student_id, action="submission.tab_hidden", resource_type="submission", resource_id=submission_id, timestamp=start_time + timedelta(seconds=5)),
        AuditLog(user_id=submission.student_id, action="submission.tab_visible", resource_type="submission", resource_id=submission_id, timestamp=start_time + timedelta(seconds=15)),
        # Попытка вставки
        AuditLog(user_id=submission.student_id, action="submission.paste_attempted", resource_type="submission", resource_id=submission_id, timestamp=start_time + timedelta(seconds=20)),
        # Конец
        AuditLog(user_id=submission.student_id, action="submission.submit", resource_type="submission", resource_id=submission_id, timestamp=start_time + timedelta(seconds=30)),
    ]
    db_session.add_all(events)
    await db_session.commit()

    # 3. Запускаем оценку с моком LLM
    with mock.patch("app.services.llm_service.llm_service.evaluate_text_answer") as mock_llm:
        mock_llm.return_value = {
            "total_score": 80,
            "criteria_scores": {},
            "feedback": "Good",
            "integrity_score": 100
        }
        
        await run_evaluate_text_answer(db_session, str(answer_id))
        
        # Проверяем, что в LLM переданы правильные настройки анти-чита
        args, kwargs = mock_llm.call_args
        config = kwargs.get("config", {})
        
        assert "event_log" in config
        assert len(config["event_log"]) == 2 # 1 away event, 1 paste event
        assert config["away_time_seconds"] == 10.0
        assert config["total_time_seconds"] == 30.0
        assert config["focus_time_seconds"] == 20.0
        
        # Проверяем записи в логе
        log = config["event_log"]
        assert log[0]["event"] == "away_from_tab"
        assert log[0]["duration"] == "10.0s"
        assert log[1]["event"] == "paste_attempted"

from datetime import timedelta
