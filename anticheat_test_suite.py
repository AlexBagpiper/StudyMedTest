
import asyncio
import json
import uuid
import os
from datetime import datetime
from sqlalchemy import select, update
from app.core.database import AsyncSessionLocal
from app.models.submission import Submission, Answer, SubmissionStatus
from app.models.question import Question, QuestionType
from app.models.test import Test, TestVariant
from app.models.audit import AuditLog
from app.tasks.evaluation_tasks import run_evaluate_text_answer
from app.models.user import User
from app.models.system_config import SystemConfig

async def run_anticheat_test():
    async with AsyncSessionLocal() as session:
        # 0. Get a real user
        res = await session.execute(select(User).limit(1))
        user = res.scalar_one_or_none()
        if not user:
            print("No user found.")
            return

        # Backup current config
        res = await session.execute(select(SystemConfig).where(SystemConfig.key == "llm_evaluation_params"))
        config_obj = res.scalar_one_or_none()
        old_config_val = config_obj.value if config_obj else None

        # 1. Create a dummy question
        q_id = uuid.uuid4()
        question = Question(
            id=q_id,
            author_id=user.id,
            type=QuestionType.TEXT,
            content="Тестовый вопрос про античит. Что такое аспирин?",
            reference_data={"reference_answer": "Аспирин - это ацетилсалициловая кислота, НПВС."},
            scoring_criteria={
                "factual_correctness": 40,
                "completeness": 30,
                "terminology": 20,
                "structure": 10
            },
            event_log_check_enabled=True,
            ai_check_enabled=True
        )
        session.add(question)
        
        sub_id = uuid.uuid4()
        res = await session.execute(select(TestVariant).limit(1))
        variant = res.scalar_one_or_none()
        submission = Submission(
            id=sub_id,
            student_id=user.id,
            variant_id=variant.id if variant else None,
            status=SubmissionStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        session.add(submission)
        await session.flush()
        
        answer = Answer(
            id=uuid.uuid4(),
            submission_id=sub_id,
            question_id=q_id,
            student_answer="Аспирин это лекарство."
        )
        session.add(answer)
        
        events_mock = [
            {"type": "paste_attempted", "time": "2026-02-13T04:02:22.163Z"},
            {"type": "paste_attempted", "time": "2026-02-13T04:02:27.096Z"}
        ]
        
        for i, ev in enumerate(events_mock):
            session.add(AuditLog(
                user_id=user.id,
                action="submission.paste_attempted",
                resource_type="submission",
                resource_id=sub_id,
                details={"question_id": str(q_id), "timestamp": ev["time"]}
            ))
        
        await session.commit()

        # 5. Run evaluation with DIFFERENT configs
        from app.core.config import settings
        # settings.YANDEX_API_KEY = "..."
        # settings.YANDEX_FOLDER_ID = "..."
        
        # Test Case 1: Custom Prompt (Expected to FAIL anti-cheat)
        print("\n--- Test Case 1: Custom Prompt from DB ---")
        eval_res = await run_evaluate_text_answer(session, str(answer.id))
        await session.refresh(answer)
        print(f"Integrity Score: {answer.evaluation.get('integrity_score')}")
        if answer.evaluation.get('integrity_score', 1.0) == 1.0:
            print("RESULT: FAILURE (as expected) - Integrity score is 1.0 even with paste events.")
        else:
            print("RESULT: SUCCESS - Integrity score is lowered.")

if __name__ == "__main__":
    asyncio.run(run_anticheat_test())
