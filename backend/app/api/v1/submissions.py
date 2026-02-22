"""
Submissions endpoints
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, Role
from app.models.submission import Submission, SubmissionStatus, Answer, RetakePermission
from app.models.test import TestVariant, Test
from app.models.question import Question
from app.schemas.submission import (
    SubmissionCreate,
    SubmissionResponse,
    PaginatedSubmissionsResponse,
    AnswerCreate,
    AnswerUpdate,
    AnswerResponse,
    BulkDeleteRequest,
    SubmissionEventCreate,
    RetakePermissionCreate,
    RetakePermissionResponse,
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
    
    # 1. Проверяем наличие существующих попыток этого студента для этого теста
    # Нам нужно найти все submissions студента для любого варианта этого же теста
    result = await db.execute(
        select(Submission)
        .join(TestVariant)
        .where(
            Submission.student_id == current_user.id,
            TestVariant.test_id == variant.test_id
        )
        .order_by(Submission.attempt_number.desc())
    )
    existing_submissions = result.scalars().all()
    
    attempt_number = 1
    if existing_submissions:
        # Если есть незавершенная попытка, возвращаем её
        in_progress = next((s for s in existing_submissions if s.status == SubmissionStatus.IN_PROGRESS), None)
        if in_progress:
            # Если это тот же вариант или мы разрешаем продолжать другой вариант (обычно тот же)
            # В текущей реализации просто возвращаем её
            return await get_submission(in_progress.id, current_user, db)

        # Если все попытки завершены, проверяем разрешение на пересдачу
        result = await db.execute(
            select(RetakePermission)
            .where(
                RetakePermission.student_id == current_user.id,
                RetakePermission.test_id == variant.test_id,
                RetakePermission.submission_id == None  # Разрешение еще не использовано
            )
            .order_by(RetakePermission.created_at.desc())
        )
        permission = result.scalar_one_or_none()
        
        if not permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Test already submitted. Request a retake from your teacher."
            )
        
        attempt_number = existing_submissions[0].attempt_number + 1
        
        # Создание submission
        submission = Submission(
            student_id=current_user.id,
            variant_id=submission_in.variant_id,
            status=SubmissionStatus.IN_PROGRESS,
            attempt_number=attempt_number
        )
        db.add(submission)
        await db.flush() # Получаем ID
        
        # Привязываем разрешение к новому submission
        permission.submission_id = submission.id
    else:
        # Первая попытка
        submission = Submission(
            student_id=current_user.id,
            variant_id=submission_in.variant_id,
            status=SubmissionStatus.IN_PROGRESS,
            attempt_number=1
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
    if submission.status == SubmissionStatus.IN_PROGRESS and not submission.answers:
        submission.started_at = datetime.utcnow()
        await db.commit()
    
    # Добавляем time_limit в объект для схемы
    submission.time_limit = submission.variant.test.settings.get("time_limit")
    
    # Вычисляем оставшееся время на сервере для точности
    if submission.status == SubmissionStatus.IN_PROGRESS and submission.time_limit:
        try:
            time_limit_int = int(submission.time_limit)
            limit_ms = time_limit_int * 60 * 1000
            elapsed_ms = (datetime.utcnow() - submission.started_at).total_seconds() * 1000
            remaining_ms = max(0, limit_ms - elapsed_ms)
            submission.remaining_seconds = int(remaining_ms / 1000)
        except (ValueError, TypeError):
            submission.remaining_seconds = None
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
            logger.error(f"Failed to start evaluation task: {e}")
        
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
        except Exception as e:
            # Мы не выбрасываем ошибку здесь, так как статус уже изменен в БД
            logger.error(f"Failed to start evaluation task: {e}")
        
        # Релоад со всеми связями ПОСЛЕ commit (важно для асинхронной сериализации)
        result = await db.execute(
            select(Submission)
            .options(
                selectinload(Submission.answers),
                selectinload(Submission.student),
                selectinload(Submission.variant).selectinload(TestVariant.test).selectinload(Test.author)
            )
            .where(Submission.id == submission_id)
        )
        submission = result.scalar_one()
        
        # Добавляем time_limit в объект для схемы
        try:
            val = submission.variant.test.settings.get("time_limit")
            submission.time_limit = int(val) if val is not None else None
        except Exception:
            submission.time_limit = None
        
        return submission
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error submitting test")
        raise HTTPException(status_code=500, detail="Internal server error") from None


@router.post("/{submission_id}/events", status_code=status.HTTP_204_NO_CONTENT)
async def log_submission_event(
    submission_id: UUID,
    event_in: SubmissionEventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Логирование событий прохождения теста (paste, tab switching и т.д.)
    """
    # Проверка submission
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
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
    
    await log_audit_action(
        db,
        current_user.id,
        f"submission.{event_in.event_type}",
        "submission",
        resource_id=submission_id,
        details=event_in.details
    )
    await db.commit()
    return None


@router.get("", response_model=PaginatedSubmissionsResponse)
async def list_submissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    student_id: UUID = None,
    test_id: UUID = None,
    include_hidden: bool = False,
    sort_by: str = "started_at",
    order: str = "desc",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Список submissions (пагинированный)
    """
    query = select(Submission).options(
        selectinload(Submission.answers),
        selectinload(Submission.student),
        selectinload(Submission.variant).selectinload(TestVariant.test).selectinload(Test.author)
    )
    count_query = select(func.count(Submission.id))
    
    # Students видят только свои submissions и всегда видят скрытые
    if current_user.role == Role.STUDENT:
        query = query.where(Submission.student_id == current_user.id)
        count_query = count_query.where(Submission.student_id == current_user.id)
    elif current_user.role == Role.TEACHER:
        query = query.join(Submission.variant).join(TestVariant.test).where(Test.author_id == current_user.id)
        count_query = count_query.join(Submission.variant).join(TestVariant.test).where(Test.author_id == current_user.id)
        if not include_hidden:
            query = query.where(Submission.is_hidden == False)
            count_query = count_query.where(Submission.is_hidden == False)
    
    if student_id and current_user.role in [Role.TEACHER, Role.ADMIN]:
        query = query.where(Submission.student_id == student_id)
        count_query = count_query.where(Submission.student_id == student_id)
    
    if test_id:
        if current_user.role == Role.TEACHER:
            query = query.where(TestVariant.test_id == test_id)
            count_query = count_query.where(TestVariant.test_id == test_id)
        else:
            query = query.join(Submission.variant).where(TestVariant.test_id == test_id)
            count_query = count_query.join(Submission.variant).where(TestVariant.test_id == test_id)
    
    total = (await db.scalar(count_query)) or 0
    
    if not hasattr(Submission, sort_by):
        sort_attr = Submission.started_at
    else:
        sort_attr = getattr(Submission, sort_by)
        if not hasattr(sort_attr, "desc"):
            sort_attr = Submission.started_at

    if order == "desc":
        query = query.order_by(sort_attr.desc())
    else:
        query = query.order_by(sort_attr.asc())
        
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    submissions = result.scalars().all()

    for sub in submissions:
        try:
            if sub.variant and sub.variant.test:
                sub.time_limit = sub.variant.test.settings.get("time_limit")
            else:
                sub.time_limit = None
        except Exception:
            sub.time_limit = None
    
    return PaginatedSubmissionsResponse(items=submissions, total=total, skip=skip, limit=limit)


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


@router.post("/{submission_id}/grant-retake", response_model=RetakePermissionResponse)
async def grant_retake(
    submission_id: UUID,
    comment: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Разрешить студенту пересдать тест
    """
    # 1. Получаем submission, чтобы узнать студента и тест
    result = await db.execute(
        select(Submission)
        .options(joinedload(Submission.variant))
        .where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # 2. Проверяем права (преподаватель - автор теста или админ)
    result = await db.execute(select(Test).where(Test.id == submission.variant.test_id))
    test = result.scalar_one()
    
    if current_user.role != Role.ADMIN and test.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # 3. Проверяем, нет ли уже активного разрешения (неиспользованного)
    result = await db.execute(
        select(RetakePermission).where(
            RetakePermission.student_id == submission.student_id,
            RetakePermission.test_id == test.id,
            RetakePermission.submission_id == None
        )
    )
    existing_permission = result.scalar_one_or_none()
    
    if existing_permission:
        # Если разрешение уже есть, просто обновляем его и возвращаем
        existing_permission.teacher_id = current_user.id
        existing_permission.comment = comment
        existing_permission.created_at = datetime.utcnow()
        await db.commit()
        await db.refresh(existing_permission)
        return existing_permission
    
    # 4. Создаем новое разрешение
    permission = RetakePermission(
        test_id=test.id,
        student_id=submission.student_id,
        teacher_id=current_user.id,
        comment=comment
    )
    db.add(permission)
    
    # Аудит
    await log_audit_action(
        db,
        current_user.id,
        "submission.grant_retake",
        "submission",
        resource_id=submission_id,
        details={"student_id": str(submission.student_id), "test_id": str(test.id)}
    )
    
    await db.commit()
    await db.refresh(permission)
    return permission


@router.get("/retake-permissions/my", response_model=List[RetakePermissionResponse])
async def list_my_retake_permissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Список разрешений на пересдачу для текущего студента
    """
    result = await db.execute(
        select(RetakePermission)
        .where(
            RetakePermission.student_id == current_user.id,
            RetakePermission.submission_id == None
        )
    )
    return result.scalars().all()


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

