"""
Authentication endpoints
"""

import secrets
import string
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.models.user import User, Role
from app.schemas.user import (
    Token, 
    UserCreate, 
    UserResponse, 
    RefreshTokenRequest,
    EmailVerificationRequest,
    ResendVerificationRequest
)
from app.services.email_service import send_verification_email
from app.core.redis import set_json, get_json, delete_key
import uuid

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Регистрация нового пользователя (данные хранятся в Redis до подтверждения email)
    """
    # Проверка существования пользователя в основной БД
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Только студенты могут регистрироваться самостоятельно
    if user_in.role != Role.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-registration is only allowed for students"
        )
    
    # Генерация кода подтверждения
    code = "".join(secrets.choice(string.digits) for _ in range(6))
    
    # Сохраняем данные в Redis (на 24 часа)
    registration_data = {
        "email": user_in.email,
        "password_hash": get_password_hash(user_in.password),
        "last_name": user_in.last_name,
        "first_name": user_in.first_name,
        "middle_name": user_in.middle_name,
        "role": user_in.role.value,
        "code": code,
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
    }
    
    await set_json(f"pending_reg:{user_in.email}", registration_data, expire=86400)
    
    # Отправка email
    await send_verification_email(user_in.email, code)
    
    # В dev режиме логируем код
    if settings.ENVIRONMENT == "development":
        import logging
        logging.getLogger(__name__).info(f"Verification code for {user_in.email}: {code}")
    
    return {"message": "Verification code sent to email", "email": user_in.email}


@router.post("/verify-email")
async def verify_email(
    data: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Подтверждение email и создание пользователя в основной БД
    """
    # Ищем данные в Redis
    reg_data = await get_json(f"pending_reg:{data.email}")
    
    if not reg_data:
        # Проверяем, может пользователь уже подтвержден?
        result = await db.execute(select(User).where(User.email == data.email))
        if result.scalar_one_or_none():
            return {"message": "Email already verified"}
            
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration request not found or expired"
        )
    
    # Проверка кода
    if reg_data["code"] != data.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Создаем пользователя в БД
    user = User(
        email=reg_data["email"],
        password_hash=reg_data["password_hash"],
        last_name=reg_data["last_name"],
        first_name=reg_data["first_name"],
        middle_name=reg_data["middle_name"],
        role=Role(reg_data["role"]),
        is_verified=True,
        is_active=True
    )
    
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
        # Удаляем данные из Redis после успешного создания
        await delete_key(f"pending_reg:{data.email}")
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user"
        )
    
    return {"message": "Email verified successfully, account created"}


@router.post("/resend-verification")
async def resend_verification(
    data: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Повторная отправка кода подтверждения (обновление в Redis)
    """
    # Ищем данные в Redis
    reg_data = await get_json(f"pending_reg:{data.email}")
    
    if not reg_data:
        # Проверяем в БД
        result = await db.execute(select(User).where(User.email == data.email))
        if result.scalar_one_or_none():
            return {"message": "Email already verified"}
            
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration request not found or expired"
        )
    
    # Генерация нового кода
    code = "".join(secrets.choice(string.digits) for _ in range(6))
    reg_data["code"] = code
    reg_data["expires_at"] = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    
    await set_json(f"pending_reg:{data.email}", reg_data, expire=86400)
    await send_verification_email(data.email, code)
    
    response = {"message": "Verification code sent"}
    if settings.ENVIRONMENT == "development":
        response["dev_code"] = code
        
    return response


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 совместимая аутентификация (username = email)
    """
    # Поиск пользователя
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    password_valid = verify_password(form_data.password, user.password_hash)
    
    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Опционально: проверка подтверждения email
    # if not user.is_verified:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Email not verified"
    #     )
    
    # Создание токенов
    access_token = create_access_token(
        subject=str(user.id),
        additional_claims={"role": user.role}
    )
    refresh_token = create_refresh_token(subject=str(user.id))
    
    # Обновление last_login
    user.last_login = datetime.utcnow()
    await db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"  # nosec B105
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Обновление access token используя refresh token
    """
    from app.core.security import decode_token
    
    try:
        payload = decode_token(token_data.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("sub")
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Создание новых токенов
        access_token = create_access_token(
            subject=str(user.id),
            additional_claims={"role": user.role}
        )
        new_refresh_token = create_refresh_token(subject=str(user.id))
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"  # nosec B105
        }
    
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate refresh token"
        )
