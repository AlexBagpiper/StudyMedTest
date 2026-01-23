"""
Tasks для оценки ответов студентов (LLM и CV)
"""

import asyncio
import logging
import json
import os
from uuid import UUID
from datetime import datetime
from typing import Dict, Any, Optional

from celery import Task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.tasks.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.submission import Submission, SubmissionStatus, Answer
from app.models.question import Question, QuestionType

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """
    Base task с async database session
    """
    def get_session(self) -> AsyncSession:
        return AsyncSessionLocal()

async def run_evaluate_text_answer(session: AsyncSession, answer_id: str) -> Dict[str, Any]:
    """Внутренняя логика оценки текста"""
    result = await session.execute(
        select(Answer).where(Answer.id == UUID(answer_id))
    )
    answer = result.scalar_one_or_none()
    if not answer: return {"error": "Answer not found"}
    
    result = await session.execute(
        select(Question).where(Question.id == answer.question_id)
    )
    question = result.scalar_one_or_none()
    
    from app.services.llm_service import llm_service
    evaluation_result = await llm_service.evaluate_text_answer(
        question=question.content,
        reference_answer=question.reference_data.get("reference_answer", "") if question.reference_data else "",
        student_answer=answer.student_answer,
        criteria=question.scoring_criteria or {}
    )
    
    answer.evaluation = {
        "criteria_scores": evaluation_result["criteria_scores"],
        "feedback": evaluation_result["feedback"],
        "llm_provider": evaluation_result["provider"],
        "evaluated_at": datetime.utcnow().isoformat(),
    }
    answer.score = round(evaluation_result["total_score"])
    return {"answer_id": answer_id, "score": answer.score}

async def run_evaluate_annotation_answer(session: AsyncSession, answer_id: str) -> Dict[str, Any]:
    """Внутренняя логика оценки аннотации"""
    result = await session.execute(
        select(Answer).where(Answer.id == UUID(answer_id))
    )
    answer = result.scalar_one_or_none()
    if not answer: return {"error": "Answer not found"}
    
    result = await session.execute(
        select(Question).where(Question.id == answer.question_id)
    )
    question = result.scalar_one_or_none()
    
    from app.services.cv_service import cv_service
    
    # Пытаемся достать эталонные аннотации из разных мест
    reference_data = question.reference_data or {}
    
    # Если в reference_data нет аннотаций, но есть в картинке (COCO формат)
    if not reference_data.get("annotations") and question.image and question.image.coco_annotations:
        reference_data = question.image.coco_annotations
    
    # Если и там нет, проверяем структуру reference_data (может там вложенный объект)
    if not reference_data.get("annotations") and isinstance(reference_data, dict):
        # Возможно, аннотации лежат в ключе 'reference_answer' как строка?
        ref_ans = reference_data.get("reference_answer")
        if isinstance(ref_ans, str) and ref_ans.startswith('{'):
            try:
                reference_data = json.loads(ref_ans)
            except Exception:
                pass

    evaluation_result = await cv_service.evaluate_annotation(
        student_data=answer.annotation_data or {},
        reference_data=reference_data,
        image_id=question.image_id
    )
    
    answer.evaluation = {
        "iou": evaluation_result["iou"],
        "recall": evaluation_result["recall"],
        "precision": evaluation_result["precision"],
        "iou_scores": evaluation_result["iou_scores"],
        "evaluated_at": datetime.utcnow().isoformat(),
    }
    answer.score = round(evaluation_result["total_score"])
    return {"answer_id": answer_id, "score": answer.score}

def run_async(coro):
    """Безопасный запуск асинхронного кода из синхронной среды Celery"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        # Если цикл уже запущен (например, в другом потоке или Celery пуле),
        # мы не можем просто запустить run_until_complete.
        # Но для solo пула в Windows обычно цикл не запущен.
        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(coro)
    else:
        return loop.run_until_complete(coro)

@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.evaluation_tasks.evaluate_text_answer")
def evaluate_text_answer(self, answer_id: str):
    async def _run():
        async with self.get_session() as session:
            try:
                res = await run_evaluate_text_answer(session, answer_id)
                await session.commit()
                return res
            except Exception as e:
                logger.exception(f"Error evaluating text answer {answer_id}")
                return {"error": str(e)}
    return run_async(_run())

@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.evaluation_tasks.evaluate_annotation_answer")
def evaluate_annotation_answer(self, answer_id: str):
    async def _run():
        async with self.get_session() as session:
            try:
                res = await run_evaluate_annotation_answer(session, answer_id)
                await session.commit()
                return res
            except Exception as e:
                logger.exception(f"Error evaluating annotation answer {answer_id}")
                return {"error": str(e)}
    return run_async(_run())

@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.evaluation_tasks.evaluate_choice_answer")
def evaluate_choice_answer(self, answer_id: str):
    async def _run():
        async with self.get_session() as session:
            try:
                result = await session.execute(
                    select(Answer).where(Answer.id == UUID(answer_id))
                )
                answer = result.scalar_one_or_none()
                if not answer: return {"error": "Answer not found"}
                
                answer.evaluation = {
                    "type": "choice",
                    "evaluated_at": datetime.utcnow().isoformat(),
                    "note": "Stub evaluation for choice question"
                }
                answer.score = 100.0
                await session.commit()
                return {"answer_id": answer_id, "score": answer.score}
            except Exception as e:
                logger.exception(f"Error evaluating choice answer {answer_id}")
                return {"error": str(e)}
    return run_async(_run())

@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.evaluation_tasks.evaluate_submission")
def evaluate_submission(self, submission_id: str):
    """
    Оценка всего submission
    """
    async def _evaluate():
        async with self.get_session() as session:
            try:
                result = await session.execute(
                    select(Submission).where(Submission.id == UUID(submission_id))
                )
                submission = result.scalar_one_or_none()
                if not submission:
                    return {"error": "Submission not found"}
                
                result = await session.execute(
                    select(Answer).where(Answer.submission_id == submission.id)
                )
                answers = result.scalars().all()
                
                for i, answer in enumerate(answers):
                    result_q = await session.execute(
                        select(Question)
                        .options(selectinload(Question.image))
                        .where(Question.id == answer.question_id)
                    )
                    question = result_q.scalar_one_or_none()
                    
                    try:
                        if not question:
                            continue

                        if question.type == QuestionType.TEXT:
                            await run_evaluate_text_answer(session, str(answer.id))
                        elif question.type == QuestionType.IMAGE_ANNOTATION:
                            await run_evaluate_annotation_answer(session, str(answer.id))
                        elif question.type == QuestionType.CHOICE:
                            answer.evaluation = {"type": "choice", "evaluated_at": datetime.utcnow().isoformat()}
                            answer.score = 100.0
                        
                    except Exception as e:
                        logger.error(f"Failed to evaluate answer {answer.id}: {e}")
                        answer.score = 0
                
                # Подсчёт итогового балла
                total_sum = sum(a.score or 0 for a in answers)
                max_possible = len(answers) * 100
                
                percentage = (total_sum / max_possible * 100) if max_possible > 0 else 0
                
                if percentage >= 90: grade = "5"
                elif percentage >= 75: grade = "4"
                elif percentage >= 60: grade = "3"
                else: grade = "2"
                
                submission.result = {
                    "total_score": round(percentage),
                    "max_score": 100,
                    "percentage": round(percentage),
                    "grade": grade,
                }
                submission.status = SubmissionStatus.COMPLETED
                submission.completed_at = datetime.utcnow()
                
                await session.commit()
                
                return {"submission_id": submission_id, "result": submission.result}
            
            except Exception as e:
                logger.exception(f"Error evaluating submission {submission_id}")
                return {"error": str(e)}
    
    try:
        return run_async(_evaluate())
    except Exception as e:
        raise
