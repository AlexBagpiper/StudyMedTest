"""
Question Pydantic схемы
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.question import QuestionType


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
    presigned_url: Optional[str] = None  # Временная URL для доступа

    model_config = {"from_attributes": True}


class QuestionBase(BaseModel):
    """
    Базовая схема вопроса
    """
    type: QuestionType
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    reference_data: Optional[Dict[str, Any]] = None
    scoring_criteria: Optional[Dict[str, Any]] = None


class QuestionCreate(QuestionBase):
    """
    Схема для создания вопроса
    """
    image_id: Optional[UUID] = None


class QuestionUpdate(BaseModel):
    """
    Схема для обновления вопроса
    """
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None, min_length=1)
    reference_data: Optional[Dict[str, Any]] = None
    scoring_criteria: Optional[Dict[str, Any]] = None
    image_id: Optional[UUID] = None


class QuestionResponse(QuestionBase):
    """
    Схема ответа с вопросом
    """
    id: UUID
    author_id: UUID
    image_id: Optional[UUID] = None
    image: Optional[ImageAssetResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

