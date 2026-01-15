"""
Topic Pydantic схемы
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TopicBase(BaseModel):
    """
    Базовая схема темы
    """
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class TopicCreate(TopicBase):
    """
    Схема для создания темы
    """
    pass


class TopicUpdate(BaseModel):
    """
    Схема для обновления темы
    """
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class TopicResponse(TopicBase):
    """
    Схема ответа с темой
    """
    id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
