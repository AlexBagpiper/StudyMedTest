"""
Tasks для оценки ответов студентов (LLM и CV)
"""

import asyncio
from uuid import UUID
from datetime import datetime

from celery import Task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.submission import Submission, SubmissionStatus, Answer
from app.models.question import Question, QuestionType


class DatabaseTask(Task):
    """
    Base task с async database session
    """
    _session = None
    
    async def get_session(self) -> AsyncSession:
        if self._session is None:
            self._session = AsyncSessionLocal()
        return self._session
    
    async def close_session(self):
        if self._session:
            await self._session.close()
            self._session = None


@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.evaluation_tasks.evaluate_text_answer")
def evaluate_text_answer(self, answer_id: str):
    """
    Оценка текстового ответа с помощью LLM
    """
    async def _evaluate():
        session = await self.get_session()
        try:
            # Получение ответа и вопроса
            result = await session.execute(
                select(Answer).where(Answer.id == UUID(answer_id))
            )
            answer = result.scalar_one_or_none()
            
            if not answer:
                return {"error": "Answer not found"}
            
            result = await session.execute(
                select(Question).where(Question.id == answer.question_id)
            )
            question = result.scalar_one_or_none()
            
            # LLM evaluation
            from app.services.llm_service import llm_service
            
            evaluation_result = await llm_service.evaluate_text_answer(
                question=question.content,
                reference_answer=question.reference_data.get("reference_answer", ""),
                student_answer=answer.student_answer,
                criteria=question.scoring_criteria or {}
            )
            
            # Сохранение результата
            answer.evaluation = {
                "criteria_scores": evaluation_result["criteria_scores"],
                "feedback": evaluation_result["feedback"],
                "llm_provider": evaluation_result["provider"],
                "evaluated_at": datetime.utcnow().isoformat(),
            }
            answer.score = evaluation_result["total_score"]
            
            await session.commit()
            
            return {
                "answer_id": answer_id,
                "score": answer.score,
                "evaluation": answer.evaluation
            }
        
        finally:
            await self.close_session()
    
    return asyncio.run(_evaluate())


@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.evaluation_tasks.evaluate_annotation_answer")
def evaluate_annotation_answer(self, answer_id: str):
    """
    Оценка графической аннотации с помощью CV алгоритмов
    """
    async def _evaluate():
        session = await self.get_session()
        try:
            # Получение ответа и вопроса
            result = await session.execute(
                select(Answer).where(Answer.id == UUID(answer_id))
            )
            answer = result.scalar_one_or_none()
            
            if not answer:
                return {"error": "Answer not found"}
            
            result = await session.execute(
                select(Question).where(Question.id == answer.question_id)
            )
            question = result.scalar_one_or_none()
            
            # CV evaluation
            from app.services.cv_service import cv_service
            
            evaluation_result = await cv_service.evaluate_annotation(
                student_data=answer.annotation_data or {},
                reference_data=question.reference_data or {},
                image_id=question.image_id
            )
            
            # Сохранение результата
            answer.evaluation = {
                "iou_scores": evaluation_result["iou_scores"],
                "accuracy": evaluation_result["accuracy"],
                "completeness": evaluation_result["completeness"],
                "precision": evaluation_result["precision"],
                "evaluated_at": datetime.utcnow().isoformat(),
            }
            answer.score = evaluation_result["total_score"]
            
            await session.commit()
            
            return {
                "answer_id": answer_id,
                "score": answer.score,
                "evaluation": answer.evaluation
            }
        
        finally:
            await self.close_session()
    
    return asyncio.run(_evaluate())


@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.evaluation_tasks.evaluate_submission")
def evaluate_submission(self, submission_id: str):
    """
    Оценка всего submission (orchestration)
    """
    async def _evaluate():
        session = await self.get_session()
        try:
            # Получение submission с ответами
            result = await session.execute(
                select(Submission).where(Submission.id == UUID(submission_id))
            )
            submission = result.scalar_one_or_none()
            
            if not submission:
                return {"error": "Submission not found"}
            
            # Получение всех ответов
            result = await session.execute(
                select(Answer).where(Answer.submission_id == submission.id)
            )
            answers = result.scalars().all()
            
            # Запуск оценки для каждого ответа
            tasks = []
            for answer in answers:
                result = await session.execute(
                    select(Question).where(Question.id == answer.question_id)
                )
                question = result.scalar_one_or_none()
                
                if question.type == QuestionType.TEXT:
                    task = evaluate_text_answer.delay(str(answer.id))
                elif question.type == QuestionType.IMAGE_ANNOTATION:
                    task = evaluate_annotation_answer.delay(str(answer.id))
                else:
                    continue
                
                tasks.append(task)
            
            # Ожидание завершения всех задач
            for task in tasks:
                task.get(timeout=600)  # 10 min timeout per answer
            
            # Обновление результата submission
            await session.refresh(submission)
            result = await session.execute(
                select(Answer).where(Answer.submission_id == submission.id)
            )
            answers = result.scalars().all()
            
            # Подсчёт итогового балла
            total_score = sum(a.score or 0 for a in answers)
            max_score = len(answers) * 100  # Предполагаем 100 баллов за вопрос
            percentage = (total_score / max_score * 100) if max_score > 0 else 0
            
            # Определение оценки (5-балльная шкала)
            if percentage >= 90:
                grade = "5"
            elif percentage >= 75:
                grade = "4"
            elif percentage >= 60:
                grade = "3"
            else:
                grade = "2"
            
            submission.result = {
                "total_score": total_score,
                "max_score": max_score,
                "percentage": percentage,
                "grade": grade,
            }
            submission.status = SubmissionStatus.COMPLETED
            submission.completed_at = datetime.utcnow()
            
            await session.commit()
            
            return {
                "submission_id": submission_id,
                "result": submission.result
            }
        
        finally:
            await self.close_session()
    
    return asyncio.run(_evaluate())

