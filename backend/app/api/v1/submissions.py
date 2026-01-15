"""
Submissions endpoints
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, Role
from app.models.submission import Submission, SubmissionStatus, Answer
from app.models.test import TestVariant, Test
from app.models.question import Question
from app.schemas.submission import (
    SubmissionCreate,
    SubmissionResponse,
    AnswerCreate,
    AnswerUpdate,
    AnswerResponse,
)

router = APIRouter()


@router.post("/", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def start_submission(
    submission_in: SubmissionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Начать прохождение теста (создание submission)
    """
    # Проверка варианта теста
    result = await db.execute(
        select(TestVariant)
        .options(selectinload(TestVariant.test))
        .where(TestVariant.id == submission_in.variant_id)
    )
    variant = result.scalar_one_or_none()
    
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test variant not found"
        )
    
    # Проверка статуса теста
    if variant.test.status != "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test is not published"
        )
    
    # Создание submission
    submission = Submission(
        student_id=current_user.id,
        variant_id=submission_in.variant_id,
        status=SubmissionStatus.IN_PROGRESS,
    )
    
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    
    return submission


@router.get("/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение submission с ответами
    """
    result = await db.execute(
        select(Submission)
        .options(selectinload(Submission.answers))
        .where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    
    # Проверка прав доступа
    if current_user.role == Role.STUDENT and submission.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return submission


@router.post("/{submission_id}/answers", response_model=AnswerResponse)
async def create_or_update_answer(
    submission_id: UUID,
    answer_in: AnswerCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Создание или обновление ответа на вопрос
    """
    # Проверка submission
    result = await db.execute(
        select(Submission).where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    
    # Проверка прав доступа
    if submission.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Проверка статуса
    if submission.status != SubmissionStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submission is not in progress"
        )
    
    # Проверка существования ответа
    result = await db.execute(
        select(Answer).where(
            Answer.submission_id == submission_id,
            Answer.question_id == answer_in.question_id
        )
    )
    existing_answer = result.scalar_one_or_none()
    
    if existing_answer:
        # Обновление существующего ответа
        existing_answer.student_answer = answer_in.student_answer
        existing_answer.annotation_data = answer_in.annotation_data
        await db.commit()
        await db.refresh(existing_answer)
        return existing_answer
    else:
        # Создание нового ответа
        answer = Answer(
            submission_id=submission_id,
            question_id=answer_in.question_id,
            student_answer=answer_in.student_answer,
            annotation_data=answer_in.annotation_data,
        )
        db.add(answer)
        await db.commit()
        await db.refresh(answer)
        return answer


@router.post("/{submission_id}/submit", response_model=SubmissionResponse)
async def submit_test(
    submission_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Отправка теста на проверку
    """
    result = await db.execute(
        select(Submission)
        .options(selectinload(Submission.answers))
        .where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    
    # Проверка прав доступа
    if submission.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Проверка статуса
    if submission.status != SubmissionStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submission already submitted"
        )
    
    # Обновление статуса
    from datetime import datetime
    submission.submitted_at = datetime.utcnow()
    submission.status = SubmissionStatus.EVALUATING
    
    await db.commit()
    
    # Запуск асинхронной оценки через Celery
    from app.tasks.evaluation_tasks import evaluate_submission
    evaluate_submission.delay(str(submission.id))
    
    await db.refresh(submission)
    return submission


@router.get("/", response_model=List[SubmissionResponse])
async def list_submissions(
    skip: int = 0,
    limit: int = 100,
    student_id: UUID = None,
    test_id: UUID = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Список submissions
    """
    query = select(Submission)
    
    # Students видят только свои submissions
    if current_user.role == Role.STUDENT:
        query = query.where(Submission.student_id == current_user.id)
    
    # Фильтры
    if student_id and current_user.role in [Role.TEACHER, Role.ADMIN]:
        query = query.where(Submission.student_id == student_id)
    
    if test_id:
        # Нужно джойн через variant
        query = query.join(TestVariant).where(TestVariant.test_id == test_id)
    
    query = query.offset(skip).limit(limit).order_by(Submission.started_at.desc())
    result = await db.execute(query)
    submissions = result.scalars().all()
    
    return submissions

