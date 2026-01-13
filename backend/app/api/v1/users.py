"""
Users endpoints
"""

import secrets
from datetime import datetime, timedelta
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_password_hash
from app.models.user import User, Role
from app.schemas.user import UserCreate, UserResponse, UserUpdate, EmailChangeRequest, EmailChangeConfirm
from app.services.email_service import send_email_change_code

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Получение информации о текущем пользователе
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Обновление профиля текущего пользователя
    """
    update_data = user_update.model_dump(exclude_unset=True)
    
    # Хеширование пароля если он изменяется
    if "password" in update_data:
        update_data["password_hash"] = get_password_hash(update_data.pop("password"))
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user


@router.post("/me/request-email-change")
async def request_email_change(
    request: EmailChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Запрос на смену email. Отправляет код подтверждения на новый email.
    """
    new_email = request.new_email
    
    # Проверяем что новый email не занят
    result = await db.execute(select(User).where(User.email == new_email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Генерируем 6-значный код
    code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
    
    # Сохраняем pending email и код
    current_user.pending_email = new_email
    current_user.email_change_code = code
    current_user.email_change_expires = datetime.utcnow() + timedelta(minutes=15)
    
    await db.commit()
    
    # Отправляем код на новый email
    await send_email_change_code(new_email, code)
    
    # В dev режиме возвращаем код в ответе для удобства тестирования
    from app.core.config import settings
    response = {"message": "Confirmation code sent to new email", "email": new_email}
    if settings.ENVIRONMENT == "development":
        response["dev_code"] = code
    
    return response


@router.post("/me/confirm-email-change")
async def confirm_email_change(
    request: EmailChangeConfirm,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Подтверждение смены email по коду из письма.
    """
    # Проверяем что есть pending email
    if not current_user.pending_email or not current_user.email_change_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending email change request"
        )
    
    # Проверяем срок действия
    if current_user.email_change_expires and current_user.email_change_expires < datetime.utcnow():
        # Очищаем просроченный запрос
        current_user.pending_email = None
        current_user.email_change_code = None
        current_user.email_change_expires = None
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation code expired"
        )
    
    # Проверяем код
    if current_user.email_change_code != request.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid confirmation code"
        )
    
    # Ещё раз проверяем что email не занят (на случай race condition)
    result = await db.execute(select(User).where(User.email == current_user.pending_email))
    if result.scalar_one_or_none():
        current_user.pending_email = None
        current_user.email_change_code = None
        current_user.email_change_expires = None
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Меняем email
    old_email = current_user.email
    current_user.email = current_user.pending_email
    current_user.pending_email = None
    current_user.email_change_code = None
    current_user.email_change_expires = None
    
    await db.commit()
    
    return {"message": "Email changed successfully", "old_email": old_email, "new_email": current_user.email}


@router.delete("/me/cancel-email-change")
async def cancel_email_change(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Отмена запроса на смену email.
    """
    current_user.pending_email = None
    current_user.email_change_code = None
    current_user.email_change_expires = None
    await db.commit()
    
    return {"message": "Email change request cancelled"}


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    role: Role = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Список пользователей (только для admin и teacher)
    """
    if current_user.role not in [Role.ADMIN, Role.TEACHER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    query = select(User)
    
    # Фильтр по роли
    if role:
        query = query.where(User.role == role)
    
    # Teacher может видеть только студентов
    if current_user.role == Role.TEACHER:
        query = query.where(User.role == Role.STUDENT)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    
    return users


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Создание пользователя (только admin может создавать teacher и admin)
    """
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can create users"
        )
    
    # Проверка существования
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    user = User(
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        last_name=user_in.last_name,
        first_name=user_in.first_name,
        middle_name=user_in.middle_name,
        role=user_in.role,
        is_active=True,
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение информации о пользователе
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Проверка прав доступа
    if current_user.role not in [Role.ADMIN, Role.TEACHER] and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Удаление пользователя (только admin)
    """
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can delete users"
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    await db.delete(user)
    await db.commit()
    
    return None

