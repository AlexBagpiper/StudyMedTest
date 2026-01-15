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
    last_name: str = Field(..., min_length=1, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    role: Role = Role.STUDENT


class UserCreate(BaseModel):
    """
    Схема для создания пользователя
    """
    email: EmailStr
    last_name: str = Field(..., min_length=1, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)
    role: Optional[Role] = Role.STUDENT


class UserUpdate(BaseModel):
    """
    Схема для обновления пользователя (email нельзя менять без подтверждения)
    """
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=6, max_length=100)
    is_active: Optional[bool] = None


class EmailChangeRequest(BaseModel):
    """
    Запрос на смену email
    """
    new_email: EmailStr


class EmailChangeConfirm(BaseModel):
    """
    Подтверждение смены email
    """
    code: str = Field(..., min_length=6, max_length=6)


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


class RefreshTokenRequest(BaseModel):
    """
    Схема запроса на обновление токена
    """
    refresh_token: str

