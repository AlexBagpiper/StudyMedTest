"""
User Pydantic схемы
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.user import Role


class UserBase(BaseModel):
    """
    Базовая схема пользователя
    """
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    role: Role = Role.STUDENT


class UserCreate(UserBase):
    """
    Схема для создания пользователя
    """
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """
    Схема для обновления пользователя
    """
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    is_active: Optional[bool] = None


class UserInDB(UserBase):
    """
    Схема пользователя из БД
    """
    id: UUID
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserResponse(UserInDB):
    """
    Схема ответа с пользователем
    """
    pass


class Token(BaseModel):
    """
    Схема JWT токена
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """
    Схема payload JWT токена
    """
    sub: str  # user_id
    role: Role
    exp: Optional[datetime] = None

