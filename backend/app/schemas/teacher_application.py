"""
Teacher Application Pydantic схемы
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.teacher_application import ApplicationStatus


class TeacherApplicationCreate(BaseModel):
    """Создание заявки преподавателя"""
    email: EmailStr
    last_name: str = Field(..., min_length=1, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)


class TeacherApplicationResponse(BaseModel):
    """Ответ с заявкой"""
    id: UUID
    email: str
    last_name: str
    first_name: str
    middle_name: Optional[str]
    phone: Optional[str]
    status: ApplicationStatus
    admin_comment: Optional[str]
    reviewed_by: Optional[UUID]
    reviewed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TeacherApplicationReview(BaseModel):
    """Рассмотрение заявки администратором"""
    admin_comment: Optional[str] = None


class TeacherApplicationApprove(TeacherApplicationReview):
    """Одобрение заявки (+ временный пароль генерируется на backend)"""
    pass


class TeacherApplicationReject(TeacherApplicationReview):
    """Отклонение заявки"""
    pass
