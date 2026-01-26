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
    result: Optional[Dict[str, Any]] = None
    answers: List[AnswerResponse] = []
    
    # Добавляем лимит времени для фронтенда
    time_limit: Optional[int] = None # в минутах
    # Оставшееся время в секундах (вычисляется на сервере для точности)
    remaining_seconds: Optional[int] = None

    model_config = {"from_attributes": True}

