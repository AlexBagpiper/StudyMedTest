"""
Authentication endpoints
"""

from datetime import timedelta

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
from app.schemas.user import Token, UserCreate, UserResponse

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Регистрация нового пользователя (только студенты могут самостоятельно регистрироваться)
    """
    # Проверка существования пользователя
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
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
    
    # Создание пользователя
    user = User(
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        last_name=user_in.last_name,
        first_name=user_in.first_name,
        middle_name=user_in.middle_name,
        role=user_in.role,
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 совместимая аутентификация (username = email)
    """
    # #region agent log
    import json
    with open(r'e:\pythonProject\StudyMedTest\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps({"sessionId": "debug-session", "runId": "initial", "hypothesisId": "A,D", "location": "auth.py:66", "message": "Login request received", "data": {"username": form_data.username, "password_length": len(form_data.password) if form_data.password else 0}, "timestamp": __import__('datetime').datetime.now().timestamp() * 1000}) + '\n')
    # #endregion
    
    # Поиск пользователя
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    # #region agent log
    with open(r'e:\pythonProject\StudyMedTest\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps({"sessionId": "debug-session", "runId": "initial", "hypothesisId": "B", "location": "auth.py:77", "message": "User lookup result", "data": {"user_found": user is not None, "email_searched": form_data.username, "user_id": str(user.id) if user else None, "user_email": user.email if user else None}, "timestamp": __import__('datetime').datetime.now().timestamp() * 1000}) + '\n')
    # #endregion
    
    if not user:
        # #region agent log
        with open(r'e:\pythonProject\StudyMedTest\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "initial", "hypothesisId": "B", "location": "auth.py:84", "message": "User not found - 401", "data": {"attempted_email": form_data.username}, "timestamp": __import__('datetime').datetime.now().timestamp() * 1000}) + '\n')
        # #endregion
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # #region agent log
    password_valid = verify_password(form_data.password, user.password_hash)
    with open(r'e:\pythonProject\StudyMedTest\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps({"sessionId": "debug-session", "runId": "initial", "hypothesisId": "C", "location": "auth.py:95", "message": "Password verification", "data": {"password_valid": password_valid, "password_hash_prefix": user.password_hash[:20] if user.password_hash else None, "password_provided_length": len(form_data.password)}, "timestamp": __import__('datetime').datetime.now().timestamp() * 1000}) + '\n')
    # #endregion
    
    if not password_valid:
        # #region agent log
        with open(r'e:\pythonProject\StudyMedTest\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "initial", "hypothesisId": "C", "location": "auth.py:102", "message": "Password invalid - 401", "data": {}, "timestamp": __import__('datetime').datetime.now().timestamp() * 1000}) + '\n')
        # #endregion
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        # #region agent log
        with open(r'e:\pythonProject\StudyMedTest\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "initial", "hypothesisId": "B", "location": "auth.py:113", "message": "User inactive - 400", "data": {"is_active": user.is_active}, "timestamp": __import__('datetime').datetime.now().timestamp() * 1000}) + '\n')
        # #endregion
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # #region agent log
    with open(r'e:\pythonProject\StudyMedTest\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps({"sessionId": "debug-session", "runId": "initial", "hypothesisId": "E", "location": "auth.py:123", "message": "Before token creation", "data": {"user_id": str(user.id), "user_role": user.role}, "timestamp": __import__('datetime').datetime.now().timestamp() * 1000}) + '\n')
    # #endregion
    
    # Создание токенов
    access_token = create_access_token(
        subject=str(user.id),
        additional_claims={"role": user.role}
    )
    refresh_token = create_refresh_token(subject=str(user.id))
    
    # #region agent log
    with open(r'e:\pythonProject\StudyMedTest\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps({"sessionId": "debug-session", "runId": "initial", "hypothesisId": "E", "location": "auth.py:137", "message": "Tokens created successfully", "data": {"access_token_length": len(access_token), "refresh_token_length": len(refresh_token)}, "timestamp": __import__('datetime').datetime.now().timestamp() * 1000}) + '\n')
    # #endregion
    
    # Обновление last_login
    from datetime import datetime
    user.last_login = datetime.utcnow()
    await db.commit()
    
    # #region agent log
    with open(r'e:\pythonProject\StudyMedTest\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps({"sessionId": "debug-session", "runId": "initial", "hypothesisId": "E", "location": "auth.py:149", "message": "Login successful - returning tokens", "data": {"user_email": user.email}, "timestamp": __import__('datetime').datetime.now().timestamp() * 1000}) + '\n')
    # #endregion
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Обновление access token используя refresh token
    """
    from app.core.security import decode_token
    
    try:
        payload = decode_token(refresh_token)
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
            "token_type": "bearer"
        }
    
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate refresh token"
        )

