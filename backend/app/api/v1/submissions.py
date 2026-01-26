"""
Submissions endpoints
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

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
    BulkDeleteRequest,
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
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
    
    # Релоад со всеми связями для ответа
    result = await db.execute(
        select(Submission)
        .options(
            selectinload(Submission.answers),
            selectinload(Submission.student),
            selectinload(Submission.variant).selectinload(TestVariant.test).selectinload(Test.author)
        )
        .where(Submission.id == submission.id)
    )
    submission = result.scalar_one()
    
    # Добавляем time_limit в объект для схемы
    submission.time_limit = submission.variant.test.settings.get("time_limit")
    
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
        .options(
            selectinload(Submission.answers),
            selectinload(Submission.student),
            selectinload(Submission.variant).selectinload(TestVariant.test).selectinload(Test.author)
        )
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
    
    # ВАЖНО: Если это первый запрос к submission (нет ответов), 
    # обновляем started_at на текущий момент
    # Это гарантирует, что таймер начинается с момента открытия страницы теста
    # #region agent log
    old_started_at = submission.started_at
    answers_count = len(submission.answers) if submission.answers else 0
    # #endregion
    if submission.status == SubmissionStatus.IN_PROGRESS and not submission.answers:
        submission.started_at = datetime.utcnow()
        await db.commit()
        # #region agent log
        print(f"[DEBUG TIMER] Updated started_at: id={submission.id}, old={old_started_at}, new={submission.started_at}, answers_count={answers_count}")
        # #endregion
    else:
        # #region agent log
        print(f"[DEBUG TIMER] Did NOT update started_at: id={submission.id}, status={submission.status}, answers_count={answers_count}, started_at={submission.started_at}")
        # #endregion
    
    # Добавляем time_limit в объект для схемы
    submission.time_limit = submission.variant.test.settings.get("time_limit")
    
    # Вычисляем оставшееся время на сервере для точности
    if submission.status == SubmissionStatus.IN_PROGRESS and submission.time_limit:
        limit_ms = submission.time_limit * 60 * 1000
        elapsed_ms = (datetime.utcnow() - submission.started_at).total_seconds() * 1000
        remaining_ms = max(0, limit_ms - elapsed_ms)
        submission.remaining_seconds = int(remaining_ms / 1000)
        # #region agent log
        print(f"[DEBUG TIMER] Calculated remaining: id={submission.id}, limit_min={submission.time_limit}, elapsed_ms={elapsed_ms}, remaining_sec={submission.remaining_seconds}")
        # #endregion
    else:
        submission.remaining_seconds = None
    
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
        select(Submission)
        .options(selectinload(Submission.variant).selectinload(TestVariant.test))
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
            detail="Submission is not in progress"
        )

    # Проверка времени
    time_limit_raw = submission.variant.test.settings.get("time_limit")
    try:
        time_limit = float(time_limit_raw) if time_limit_raw is not None else None
    except (ValueError, TypeError):
        time_limit = None

    is_late = False
    if time_limit is not None:
        if datetime.utcnow() > submission.started_at + timedelta(minutes=time_limit):
            is_late = True
    
    # Сохранение ответа (даже если время вышло, мы фиксируем последнее состояние)
    result = await db.execute(
        select(Answer).where(
            Answer.submission_id == submission_id,
            Answer.question_id == answer_in.question_id
        )
    )
    existing_answer = result.scalar_one_or_none()
    
    if existing_answer:
        existing_answer.student_answer = answer_in.student_answer
        existing_answer.annotation_data = answer_in.annotation_data
    else:
        answer = Answer(
            submission_id=submission_id,
            question_id=answer_in.question_id,
            student_answer=answer_in.student_answer,
            annotation_data=answer_in.annotation_data,
        )
        db.add(answer)
    
    await db.commit()

    # Если время вышло, завершаем тест после сохранения последнего ответа
    if is_late:
        submission.status = SubmissionStatus.EVALUATING
        submission.submitted_at = submission.started_at + timedelta(minutes=time_limit)
        await db.commit()
        
        # Запуск асинхронной оценки через Celery
        try:
            from app.tasks.evaluation_tasks import evaluate_submission
            evaluate_submission.delay(str(submission.id))
        except Exception as e:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Time limit exceeded. Test submitted automatically."
        )

    # Рефреш для возврата
    if existing_answer:
        await db.refresh(existing_answer)
        return existing_answer
    else:
        # Нам нужно получить созданный объект, если мы его только что добавили
        result = await db.execute(
            select(Answer).where(
                Answer.submission_id == submission_id,
                Answer.question_id == answer_in.question_id
            )
        )
        new_answer = result.scalar_one()
        return new_answer


@router.post("/{submission_id}/submit", response_model=SubmissionResponse)
async def submit_test(
    submission_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Отправка теста на проверку
    """
    try:
        result = await db.execute(
            select(Submission)
            .options(
                selectinload(Submission.answers),
                joinedload(Submission.student),
                joinedload(Submission.variant).joinedload(TestVariant.test).joinedload(Test.author)
            )
            .where(Submission.id == submission_id)
        )
        submission = result.unique().scalar_one_or_none()
        
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
            # Если уже завершено или оценивается, просто возвращаем текущее состояние
            if submission.status in [SubmissionStatus.EVALUATING, SubmissionStatus.COMPLETED]:
                return submission
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Submission already submitted"
            )
        
        # Обновление статуса
        submission.submitted_at = datetime.utcnow()
        
        # Дополнительная проверка времени при сабмите
        time_limit_raw = submission.variant.test.settings.get("time_limit")
        try:
            time_limit = float(time_limit_raw) if time_limit_raw is not None else None
        except (ValueError, TypeError):
            time_limit = None

        if time_limit is not None and submission.submitted_at > submission.started_at + timedelta(minutes=time_limit):
            submission.submitted_at = submission.started_at + timedelta(minutes=time_limit)

        submission.status = SubmissionStatus.EVALUATING
        
        await db.commit()
        
        # Запуск асинхронной оценки через Celery
        try:
            from app.tasks.evaluation_tasks import evaluate_submission
            evaluate_submission.delay(str(submission.id))
        except Exception:
            # Мы не выбрасываем ошибку здесь, так как статус уже изменен в БД
            pass
        
        # Релоад со всеми связями ПОСЛЕ commit (важно для асинхронной сериализации)
        result = await db.execute(
            select(Submission)
            .options(
                selectinload(Submission.answers),
                joinedload(Submission.student),
                joinedload(Submission.variant).joinedload(TestVariant.test).joinedload(Test.author)
            )
            .where(Submission.id == submission_id)
        )
        submission = result.unique().scalar_one()
        
        # Добавляем time_limit в объект для схемы
        try:
            val = submission.variant.test.settings.get("time_limit")
            submission.time_limit = int(val) if val is not None else None
        except Exception:
            submission.time_limit = None
        
        # Явно конвертируем в схему ВНУТРИ сессии
        from app.schemas.submission import SubmissionResponse
        return SubmissionResponse.model_validate(submission)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error submitting test")
        raise HTTPException(status_code=500, detail="Internal server error") from None


@router.get("", response_model=List[SubmissionResponse])
async def list_submissions(
    skip: int = 0,
    limit: int = 100,
    student_id: UUID = None,
    test_id: UUID = None,
    include_hidden: bool = False,
    sort_by: str = "started_at",
    order: str = "desc",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Список submissions
    """
    query = select(Submission).options(
        selectinload(Submission.answers),
        selectinload(Submission.student),
        selectinload(Submission.variant).selectinload(TestVariant.test).selectinload(Test.author)
    )
    
    # Students видят только свои submissions и всегда видят скрытые
    if current_user.role == Role.STUDENT:
        query = query.where(Submission.student_id == current_user.id)
    elif current_user.role == Role.TEACHER:
        # Преподаватели видят только результаты по своим тестам
        query = query.join(Submission.variant).join(TestVariant.test).where(Test.author_id == current_user.id)
        # Преподаватели видят скрытые только если явно указано
        if not include_hidden:
            query = query.where(Submission.is_hidden == False)
    # Админы видят всё по умолчанию, фильтр is_hidden не применяется
    
    # Фильтры
    if student_id and current_user.role in [Role.TEACHER, Role.ADMIN]:
        query = query.where(Submission.student_id == student_id)
    
    if test_id:
        # Нужно джойн через variant
        query = query.join(Submission.variant).where(TestVariant.test_id == test_id)
    
    # Сортировка
    if not hasattr(Submission, sort_by):
        sort_attr = Submission.started_at
    else:
        sort_attr = getattr(Submission, sort_by)
        # Проверяем, что это атрибут SQLAlchemy
        if not hasattr(sort_attr, "desc"):
            sort_attr = Submission.started_at

    if order == "desc":
        query = query.order_by(sort_attr.desc())
    else:
        query = query.order_by(sort_attr.asc())
        
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    submissions = result.scalars().all()

    # Добавляем time_limit для каждого элемента списка
    for sub in submissions:
        try:
            if sub.variant and sub.variant.test:
                sub.time_limit = sub.variant.test.settings.get("time_limit")
            else:
                sub.time_limit = None
        except Exception:
            sub.time_limit = None
    
    return submissions


@router.patch("/{submission_id}/hide", response_model=SubmissionResponse)
async def hide_submission(
    submission_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Скрыть submission
    """
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    
    # Разрешено только преподавателям
    if current_user.role != Role.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can hide submissions"
        )
    
    # Проверка владения тестом
    result = await db.execute(
        select(Test)
        .join(TestVariant, Test.id == TestVariant.test_id)
        .where(TestVariant.id == submission.variant_id)
    )
    test = result.scalar_one_or_none()
    
    if not test or test.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teachers can only hide submissions for their own tests."
        )
    
    submission.is_hidden = True
    await db.commit()
    await db.refresh(submission)
    
    # Reload with relations for the response
    result = await db.execute(
        select(Submission)
        .options(
            selectinload(Submission.answers),
            selectinload(Submission.student),
            selectinload(Submission.variant).selectinload(TestVariant.test).selectinload(Test.author)
        )
        .where(Submission.id == submission.id)
    )
    submission = result.scalar_one()
    submission.time_limit = submission.variant.test.settings.get("time_limit")
    
    return submission


@router.patch("/{submission_id}/restore", response_model=SubmissionResponse)
async def restore_submission(
    submission_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Восстановить скрытый submission
    """
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    
    # Разрешено только преподавателям
    if current_user.role != Role.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can restore submissions"
        )
    
    # Проверка владения тестом (аналогично hide_submission)
    result = await db.execute(
        select(Test)
        .join(TestVariant, Test.id == TestVariant.test_id)
        .where(TestVariant.id == submission.variant_id)
    )
    test = result.scalar_one_or_none()
    
    if not test or test.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teachers can only restore submissions for their own tests."
        )
    
    submission.is_hidden = False
    await db.commit()
    await db.refresh(submission)
    
    # Reload with relations for the response
    result = await db.execute(
        select(Submission)
        .options(
            selectinload(Submission.answers),
            selectinload(Submission.student),
            selectinload(Submission.variant).selectinload(TestVariant.test).selectinload(Test.author)
        )
        .where(Submission.id == submission.id)
    )
    submission = result.scalar_one()
    submission.time_limit = submission.variant.test.settings.get("time_limit")
    
    return submission


@router.delete("/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_submission(
    submission_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Удаление submission (только владельцем или админом)
    """
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    
    # Проверка прав: только администратор
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete submissions"
        )
    
    await db.delete(submission)
    await db.commit()
    return None


async def log_audit_action(
    db: AsyncSession,
    user_id: UUID,
    action: str,
    resource_type: str,
    resource_id: UUID = None,
    details: dict = None
):
    """Логирование действий для аудита"""
    from app.models.audit import AuditLog
    audit = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details
    )
    db.add(audit)


@router.post("/bulk-delete", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_delete_submissions(
    request: BulkDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Массовое удаление submissions (только для админов)
    """
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can bulk delete submissions"
        )
    
    # 1. Получаем submissions через ORM для срабатывания каскадного удаления
    result = await db.execute(select(Submission).where(Submission.id.in_(request.ids)))
    submissions = result.scalars().all()
    
    if len(submissions) == 0:
        return None  # Ничего не удаляем, если ничего не найдено

    # 2. Удаляем через ORM для срабатывания каскада
    for submission in submissions:
        await db.delete(submission)
    deleted_count = len(submissions)
    
    await db.commit()

    # 3. Аудит лог (аналогично одиночному удалению)
    await log_audit_action(
        db, 
        current_user.id, 
        "submission.bulk_delete", 
        "submission", 
        details={"ids": [str(sub.id) for sub in submissions], "count": deleted_count}
    )
    await db.commit()

    return None

