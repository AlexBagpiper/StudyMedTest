"""
Question Pydantic схемы
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.user import Role
from app.models.question import QuestionType
from app.schemas.topic import TopicResponse
from app.schemas.annotation import AnnotationData


class ImageAssetResponse(BaseModel):
    """
    Схема ответа для ImageAsset
    """
    id: UUID
    filename: str
    storage_path: str
    width: int
    height: int
    file_size: int
    coco_annotations: Optional[Any] = None  # COCO аннотации
    presigned_url: Optional[str] = None  # Временная URL для доступа

    model_config = {"from_attributes": True}


class QuestionBase(BaseModel):
    """
    Базовая схема вопроса
    """
    type: QuestionType
    content: str = Field(..., min_length=1)
    topic_id: Optional[UUID] = None
    difficulty: int = Field(default=1, ge=1, le=5)
    reference_data: Optional[Any] = None
    scoring_criteria: Optional[Any] = None
    ai_check_enabled: bool = False
    plagiarism_check_enabled: bool = False
    event_log_check_enabled: bool = False


class QuestionCreate(QuestionBase):
    """
    Схема для создания вопроса
    """
    image_id: Optional[UUID] = None


class QuestionUpdate(BaseModel):
    """
    Схема для обновления вопроса
    """
    content: Optional[str] = Field(None, min_length=1)
    topic_id: Optional[UUID] = None
    difficulty: Optional[int] = Field(None, ge=1, le=5)
    reference_data: Optional[Any] = None
    scoring_criteria: Optional[Any] = None
    ai_check_enabled: Optional[bool] = None
    plagiarism_check_enabled: Optional[bool] = None
    event_log_check_enabled: Optional[bool] = None
    image_id: Optional[UUID] = None


class QuestionAuthor(BaseModel):
    id: UUID
    role: Role

    model_config = {"from_attributes": True}


class QuestionResponse(QuestionBase):
    """
    Схема ответа с вопросом
    """
    id: UUID
    author_id: UUID
    author: Optional[QuestionAuthor] = None
    topic: Optional[TopicResponse] = None
    image_id: Optional[UUID] = None
    image: Optional[ImageAssetResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedQuestionsResponse(BaseModel):
    """Пагинированный список вопросов"""
    items: List[QuestionResponse]
    total: int
    skip: int
    limit: int

