"""
Admin API - CRUD операции для всех сущностей
Только для роли admin
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user, get_password_hash
from app.core.storage import storage_service
from app.models.user import User, Role
from app.models.question import Question, ImageAsset
from app.models.test import Test, TestQuestion, TestVariant, TestStatus
from app.models.submission import Submission, Answer, SubmissionStatus
from app.models.audit import AuditLog
from app.schemas.admin import (
    AdminUserCreate, AdminUserUpdate, AdminUserResponse,
    AdminQuestionUpdate, AdminQuestionResponse,
    AdminTestUpdate, AdminTestResponse,
    AdminSubmissionResponse, AdminAnswerResponse,
    AdminAuditLogResponse, AdminImageAssetResponse,
    PaginatedResponse, AdminStatsResponse, EntityCounts,
)

router = APIRouter()


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Проверка что пользователь - администратор"""
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def log_admin_action(
    db: AsyncSession,
    user: User,
    action: str,
    resource_type: str,
    resource_id: UUID = None,
    details: Dict = None
):
    """Логирование админ-действий"""
    audit = AuditLog(
        user_id=user.id,
        action=f"admin.{action}",
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
    )
    db.add(audit)


# ==================== STATISTICS ====================

@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Получение общей статистики для дашборда админа"""
    users_count = await db.scalar(select(func.count(User.id)))
    students_count = await db.scalar(select(func.count(User.id)).where(User.role == Role.STUDENT))
    teachers_count = await db.scalar(select(func.count(User.id)).where(User.role == Role.TEACHER))
    admins_count = await db.scalar(select(func.count(User.id)).where(User.role == Role.ADMIN))
    
    questions_count = await db.scalar(select(func.count(Question.id)))
    tests_count = await db.scalar(select(func.count(Test.id)))
    published_tests = await db.scalar(
        select(func.count(Test.id)).where(Test.status == TestStatus.PUBLISHED)
    )
    submissions_count = await db.scalar(select(func.count(Submission.id)))
    completed_submissions = await db.scalar(
        select(func.count(Submission.id)).where(Submission.status == SubmissionStatus.COMPLETED)
    )
    images_count = await db.scalar(select(func.count(ImageAsset.id)))
    
    return AdminStatsResponse(
        users=EntityCounts(
            total=users_count or 0,
            students=students_count or 0,
            teachers=teachers_count or 0,
            admins=admins_count or 0,
        ),
        questions_count=questions_count or 0,
        tests_count=tests_count or 0,
        published_tests_count=published_tests or 0,
        submissions_count=submissions_count or 0,
        completed_submissions_count=completed_submissions or 0,
        images_count=images_count or 0,
    )


# ==================== USERS ====================

@router.get("/users", response_model=PaginatedResponse[AdminUserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    role: Optional[Role] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Список всех пользователей с фильтрами"""
    query = select(User)
    count_query = select(func.count(User.id))
    
    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)
    
    if search:
        search_filter = or_(
            User.email.ilike(f"%{search}%"),
            User.last_name.ilike(f"%{search}%"),
            User.first_name.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    total = await db.scalar(count_query)
    
    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    
    return PaginatedResponse(
        items=users,
        total=total or 0,
        skip=skip,
        limit=limit,
    )


@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Получение пользователя по ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.post("/users", response_model=AdminUserResponse, status_code=201)
async def create_user(
    user_in: AdminUserCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Создание нового пользователя"""
    # Проверка уникальности email
    existing = await db.execute(select(User).where(User.email == user_in.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        last_name=user_in.last_name,
        first_name=user_in.first_name,
        middle_name=user_in.middle_name,
        role=user_in.role,
        is_active=user_in.is_active,
        is_verified=user_in.is_verified,
    )
    
    db.add(user)
    await log_admin_action(db, admin, "create", "user", details={"email": user_in.email})
    await db.commit()
    await db.refresh(user)
    
    return user


@router.put("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: UUID,
    user_update: AdminUserUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Обновление пользователя"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_update.model_dump(exclude_unset=True, mode='json')
    
    # Проверка уникальности email
    if "email" in update_data and update_data["email"] != user.email:
        existing = await db.execute(select(User).where(User.email == update_data["email"]))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Хеширование пароля
    if "password" in update_data:
        update_data["password_hash"] = get_password_hash(update_data.pop("password"))
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await log_admin_action(db, admin, "update", "user", user_id, update_data)
    await db.commit()
    await db.refresh(user)
    
    return user


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Удаление пользователя"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    await log_admin_action(db, admin, "delete", "user", user_id, {"email": user.email})
    await db.delete(user)
    await db.commit()


# ==================== QUESTIONS ====================

@router.get("/questions", response_model=PaginatedResponse[AdminQuestionResponse])
async def list_questions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    author_id: Optional[UUID] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Список всех вопросов"""
    query = select(Question).options(
        selectinload(Question.author), 
        selectinload(Question.image),
        selectinload(Question.topic)
    )
    count_query = select(func.count(Question.id))
    
    if search:
        search_filter = or_(
            Question.content.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    if author_id:
        query = query.where(Question.author_id == author_id)
        count_query = count_query.where(Question.author_id == author_id)
    
    total = await db.scalar(count_query)
    
    query = query.order_by(Question.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    questions = result.scalars().all()
    
    # Генерация presigned URLs
    for question in questions:
        if question.image:
            question.image.presigned_url = storage_service.get_presigned_url(
                question.image.storage_path.split("/", 1)[1],
                expires_seconds=3600
            )
            
    return PaginatedResponse(items=questions, total=total or 0, skip=skip, limit=limit)


@router.get("/questions/{question_id}", response_model=AdminQuestionResponse)
async def get_question(
    question_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Получение вопроса по ID"""
    result = await db.execute(
        select(Question)
        .options(
            selectinload(Question.author), 
            selectinload(Question.image),
            selectinload(Question.topic)
        )
        .where(Question.id == question_id)
    )
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Генерация presigned URL
    if question.image:
        question.image.presigned_url = storage_service.get_presigned_url(
            question.image.storage_path.split("/", 1)[1],
            expires_seconds=3600
        )
        
    return question


@router.put("/questions/{question_id}", response_model=AdminQuestionResponse)
async def update_question(
    question_id: UUID,
    question_update: AdminQuestionUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Обновление вопроса"""
    result = await db.execute(
        select(Question)
        .options(selectinload(Question.author), selectinload(Question.image))
        .where(Question.id == question_id)
    )
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    update_data = question_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if field in ['reference_data', 'scoring_criteria'] and value is not None:
            import json
            value = json.loads(json.dumps(value, default=str))
        setattr(question, field, value)
    
    await log_admin_action(db, admin, "update", "question", question_id, update_data)
    await db.commit()
    
    # Получаем обновленный вопрос
    result = await db.execute(
        select(Question)
        .options(
            selectinload(Question.author), 
            selectinload(Question.image),
            selectinload(Question.topic)
        )
        .where(Question.id == question_id)
    )
    question = result.scalar_one()
    
    if question.image:
        question.image.presigned_url = storage_service.get_presigned_url(
            question.image.storage_path.split("/", 1)[1],
            expires_seconds=3600
        )
        
    return question


@router.delete("/questions/{question_id}", status_code=204)
async def delete_question(
    question_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Удаление вопроса"""
    result = await db.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    await log_admin_action(db, admin, "delete", "question", question_id)
    await db.delete(question)
    await db.commit()


# ==================== TESTS ====================

@router.get("/tests", response_model=PaginatedResponse[AdminTestResponse])
async def list_tests(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[TestStatus] = None,
    author_id: Optional[UUID] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Список всех тестов"""
    query = select(Test).options(selectinload(Test.author))
    count_query = select(func.count(Test.id))
    
    if search:
        search_filter = or_(
            Test.title.ilike(f"%{search}%"),
            Test.description.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    if status:
        query = query.where(Test.status == status)
        count_query = count_query.where(Test.status == status)
    
    if author_id:
        query = query.where(Test.author_id == author_id)
        count_query = count_query.where(Test.author_id == author_id)
    
    total = await db.scalar(count_query)
    
    query = query.order_by(Test.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    tests = result.scalars().all()
    
    return PaginatedResponse(items=tests, total=total or 0, skip=skip, limit=limit)


@router.get("/tests/{test_id}", response_model=AdminTestResponse)
async def get_test(
    test_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Получение теста по ID"""
    result = await db.execute(
        select(Test)
        .options(selectinload(Test.author))
        .where(Test.id == test_id)
    )
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    return test


@router.put("/tests/{test_id}", response_model=AdminTestResponse)
async def update_test(
    test_id: UUID,
    test_update: AdminTestUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Обновление теста"""
    result = await db.execute(
        select(Test).options(selectinload(Test.author)).where(Test.id == test_id)
    )
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    update_data = test_update.model_dump(exclude_unset=True, mode='json')
    
    # Обновление published_at при изменении статуса
    if "status" in update_data:
        if update_data["status"] == TestStatus.PUBLISHED and test.status != TestStatus.PUBLISHED:
            test.published_at = datetime.utcnow()
    
    for field, value in update_data.items():
        setattr(test, field, value)
    
    await log_admin_action(db, admin, "update", "test", test_id, update_data)
    await db.commit()
    await db.refresh(test)
    
    return test


@router.delete("/tests/{test_id}", status_code=204)
async def delete_test(
    test_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Удаление теста"""
    result = await db.execute(select(Test).where(Test.id == test_id))
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    await log_admin_action(db, admin, "delete", "test", test_id)
    await db.delete(test)
    await db.commit()


# ==================== SUBMISSIONS ====================

@router.get("/submissions", response_model=PaginatedResponse[AdminSubmissionResponse])
async def list_submissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    student_id: Optional[UUID] = None,
    status: Optional[SubmissionStatus] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Список всех submissions"""
    query = select(Submission).options(
        selectinload(Submission.student),
        selectinload(Submission.variant).selectinload(TestVariant.test)
    )
    count_query = select(func.count(Submission.id))
    
    if student_id:
        query = query.where(Submission.student_id == student_id)
        count_query = count_query.where(Submission.student_id == student_id)
    
    if status:
        query = query.where(Submission.status == status)
        count_query = count_query.where(Submission.status == status)
    
    total = await db.scalar(count_query)
    
    query = query.order_by(Submission.started_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    submissions = result.scalars().all()
    
    return PaginatedResponse(items=submissions, total=total or 0, skip=skip, limit=limit)


@router.get("/submissions/{submission_id}", response_model=AdminSubmissionResponse)
async def get_submission(
    submission_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Получение submission по ID"""
    result = await db.execute(
        select(Submission)
        .options(
            selectinload(Submission.student),
            selectinload(Submission.variant).selectinload(TestVariant.test),
            selectinload(Submission.answers).selectinload(Answer.question),
        )
        .where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return submission


@router.delete("/submissions/{submission_id}", status_code=204)
async def delete_submission(
    submission_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Удаление submission"""
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    await log_admin_action(db, admin, "delete", "submission", submission_id)
    await db.delete(submission)
    await db.commit()


# ==================== IMAGES ====================

@router.get("/images", response_model=PaginatedResponse[AdminImageAssetResponse])
async def list_images(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Список всех изображений"""
    total = await db.scalar(select(func.count(ImageAsset.id)))
    
    query = select(ImageAsset).order_by(ImageAsset.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    images = result.scalars().all()
    
    # Генерация presigned URLs
    for image in images:
        image.presigned_url = storage_service.get_presigned_url(
            image.storage_path.split("/", 1)[1],
            expires_seconds=3600
        )
    
    return PaginatedResponse(items=images, total=total or 0, skip=skip, limit=limit)


@router.delete("/images/{image_id}", status_code=204)
async def delete_image(
    image_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Удаление изображения"""
    result = await db.execute(select(ImageAsset).where(ImageAsset.id == image_id))
    image = result.scalar_one_or_none()
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # TODO: Удалить файл из S3/MinIO
    
    await log_admin_action(db, admin, "delete", "image", image_id)
    await db.delete(image)
    await db.commit()


# ==================== AUDIT LOGS ====================

@router.get("/audit-logs", response_model=PaginatedResponse[AdminAuditLogResponse])
async def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user_id: Optional[UUID] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Список audit логов"""
    query = select(AuditLog).options(selectinload(AuditLog.user))
    count_query = select(func.count(AuditLog.id))
    
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
        count_query = count_query.where(AuditLog.user_id == user_id)
    
    if action:
        query = query.where(AuditLog.action.ilike(f"%{action}%"))
        count_query = count_query.where(AuditLog.action.ilike(f"%{action}%"))
    
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
        count_query = count_query.where(AuditLog.resource_type == resource_type)
    
    total = await db.scalar(count_query)
    
    query = query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return PaginatedResponse(items=logs, total=total or 0, skip=skip, limit=limit)
