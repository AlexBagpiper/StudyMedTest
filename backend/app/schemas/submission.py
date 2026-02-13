"""
Submission Pydantic схемы
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.submission import SubmissionStatus
from app.schemas.user import UserResponse


class AnswerCreate(BaseModel):
    """
    Схема для создания/обновления ответа
    """
    question_id: UUID
    student_answer: Optional[str] = None
    annotation_data: Optional[Dict[str, Any]] = None


class AnswerUpdate(BaseModel):
    """
    Схема для обновления ответа
    """
    student_answer: Optional[str] = None
    annotation_data: Optional[Dict[str, Any]] = None


class AnswerResponse(BaseModel):
    """
    Схема ответа на вопрос
    """
    id: UUID
    submission_id: UUID
    question_id: UUID
    student_answer: Optional[str] = None
    annotation_data: Optional[Dict[str, Any]] = None
    annotation_file_path: Optional[str] = None
    evaluation: Optional[Dict[str, Any]] = None
    score: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BulkDeleteRequest(BaseModel):
    """
    Схема для массового удаления
    """
    ids: List[UUID]


class SubmissionEventCreate(BaseModel):
    """
    Схема для логирования событий прохождения теста
    """
    event_type: str
    details: Optional[Dict[str, Any]] = None


class SubmissionCreate(BaseModel):
    """
    Схема для создания submission
    """
    variant_id: UUID


class SubmissionResponse(BaseModel):
    """
    Схема ответа с submission
    """
    id: UUID
    student_id: UUID
    student: Optional[UserResponse] = None
    variant_id: UUID
    test_id: Optional[UUID] = None
    test_title: Optional[str] = None
    teacher: Optional[UserResponse] = None
    status: SubmissionStatus
    started_at: datetime
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    is_hidden: bool = False
    attempt_number: int = 1
    result: Optional[Dict[str, Any]] = None
    answers: List[AnswerResponse] = []
    
    # Добавляем лимит времени для фронтенда
    time_limit: Optional[int] = None # в минутах
    # Оставшееся время в секундах (вычисляется на сервере для точности)
    remaining_seconds: Optional[int] = None

    model_config = {"from_attributes": True}


class RetakePermissionCreate(BaseModel):
    """
    Схема для выдачи разрешения на пересдачу
    """
    student_id: UUID
    test_id: UUID
    comment: Optional[str] = None


class RetakePermissionResponse(BaseModel):
    """
    Схема ответа для разрешения на пересдачу
    """
    id: UUID
    test_id: UUID
    student_id: UUID
    teacher_id: UUID
    submission_id: Optional[UUID] = None
    comment: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

