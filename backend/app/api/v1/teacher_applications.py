"""
Teacher Applications endpoints
"""

import secrets
import string
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_password_hash, get_current_user, require_role
from app.models.user import User, Role
from app.models.teacher_application import TeacherApplication, ApplicationStatus
from app.schemas.teacher_application import (
    TeacherApplicationCreate,
    TeacherApplicationResponse,
    TeacherApplicationApprove,
    TeacherApplicationReject,
)
from app.services.email_service import (
    send_teacher_application_notification,
    send_teacher_account_created,
    send_teacher_application_rejected,
)

router = APIRouter()


def generate_temporary_password(length: int = 12) -> str:
    """Генерация временного пароля"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    # Обеспечиваем наличие разных типов символов
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*"),
    ]
    password += [secrets.choice(alphabet) for _ in range(length - 4)]
    secrets.SystemRandom().shuffle(password)
    return "".join(password)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=TeacherApplicationResponse)
async def create_teacher_application(
    application_in: TeacherApplicationCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Создание заявки на регистрацию преподавателя (публичный endpoint)
    """
    # Проверка существования пользователя с таким email
    result = await db.execute(select(User).where(User.email == application_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Проверка существующей заявки
    result = await db.execute(
        select(TeacherApplication).where(
            TeacherApplication.email == application_in.email,
            TeacherApplication.status == ApplicationStatus.PENDING
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application for this email already exists and is pending"
        )
    
    # Создание заявки
    application = TeacherApplication(**application_in.model_dump())
    db.add(application)
    await db.commit()
    await db.refresh(application)
    
    # Отправка уведомления администраторам
    # Получаем всех админов
    result = await db.execute(select(User).where(User.role == Role.ADMIN, User.is_active == True))
    admins = result.scalars().all()
    
    full_name = f"{application.last_name} {application.first_name}"
    if application.middle_name:
        full_name += f" {application.middle_name}"
    
    for admin in admins:
        await send_teacher_application_notification(
            admin.email,
            application.email,
            full_name
        )
    
    return application


@router.get("/", response_model=List[TeacherApplicationResponse])
async def list_teacher_applications(
    status_filter: ApplicationStatus | None = None,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
):
    """
    Список заявок преподавателей (только для админа)
    """
    query = select(TeacherApplication)
    
    if status_filter:
        query = query.where(TeacherApplication.status == status_filter)
    
    query = query.order_by(TeacherApplication.created_at.desc())
    
    result = await db.execute(query)
    applications = result.scalars().all()
    
    return applications


@router.get("/{application_id}", response_model=TeacherApplicationResponse)
async def get_teacher_application(
    application_id: UUID,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение конкретной заявки (только для админа)
    """
    result = await db.execute(
        select(TeacherApplication).where(TeacherApplication.id == application_id)
    )
    application = result.scalar_one_or_none()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    return application


@router.post("/{application_id}/approve", response_model=TeacherApplicationResponse)
async def approve_teacher_application(
    application_id: UUID,
    review_data: TeacherApplicationApprove,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
):
    """
    Одобрение заявки и создание аккаунта преподавателя (только для админа)
    """
    # Получаем заявку
    result = await db.execute(
        select(TeacherApplication).where(TeacherApplication.id == application_id)
    )
    application = result.scalar_one_or_none()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.status != ApplicationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application is already processed"
        )
    
    # Проверяем, не создан ли уже пользователь с таким email
    result = await db.execute(select(User).where(User.email == application.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Генерация временного пароля
    temp_password = generate_temporary_password()
    
    # Создание пользователя-преподавателя
    teacher = User(
        email=application.email,
        password_hash=get_password_hash(temp_password),
        last_name=application.last_name,
        first_name=application.first_name,
        middle_name=application.middle_name,
        role=Role.TEACHER,
        is_verified=True,  # Автоматически подтверждаем email
        is_active=True
    )
    
    db.add(teacher)
    
    # Обновление статуса заявки
    application.status = ApplicationStatus.APPROVED
    application.reviewed_by = current_user.id
    application.reviewed_at = datetime.utcnow()
    application.admin_comment = review_data.admin_comment
    
    try:
        await db.commit()
        await db.refresh(application)
        await db.refresh(teacher)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating teacher account"
        )
    
    # Отправка письма преподавателю с временным паролем
    full_name = f"{application.last_name} {application.first_name}"
    if application.middle_name:
        full_name += f" {application.middle_name}"
    
    await send_teacher_account_created(
        application.email,
        full_name,
        temp_password
    )
    
    return application


@router.post("/{application_id}/reject", response_model=TeacherApplicationResponse)
async def reject_teacher_application(
    application_id: UUID,
    review_data: TeacherApplicationReject,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
):
    """
    Отклонение заявки (только для админа)
    """
    # Получаем заявку
    result = await db.execute(
        select(TeacherApplication).where(TeacherApplication.id == application_id)
    )
    application = result.scalar_one_or_none()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.status != ApplicationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application is already processed"
        )
    
    # Обновление статуса
    application.status = ApplicationStatus.REJECTED
    application.reviewed_by = current_user.id
    application.reviewed_at = datetime.utcnow()
    application.admin_comment = review_data.admin_comment
    
    await db.commit()
    await db.refresh(application)
    
    # Отправка письма преподавателю об отклонении
    full_name = f"{application.last_name} {application.first_name}"
    if application.middle_name:
        full_name += f" {application.middle_name}"
    
    await send_teacher_application_rejected(
        application.email,
        full_name,
        review_data.admin_comment
    )
    
    return application
