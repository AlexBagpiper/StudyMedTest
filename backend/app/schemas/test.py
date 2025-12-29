"""
Test Pydantic схемы
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.test import TestStatus


class TestQuestionCreate(BaseModel):
    """
    Схема для добавления вопроса в тест
    """
    question_id: UUID
    order: int
    weight: int = 1


class TestBase(BaseModel):
    """
    Базовая схема теста
    """
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)


class TestCreate(TestBase):
    """
    Схема для создания теста
    """
    questions: List[TestQuestionCreate] = Field(default_factory=list)


class TestUpdate(BaseModel):
    """
    Схема для обновления теста
    """
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    status: Optional[TestStatus] = None


class TestResponse(TestBase):
    """
    Схема ответа с тестом
    """
    id: UUID
    author_id: UUID
    status: TestStatus
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Можно добавить список вопросов
    # questions: List[QuestionResponse] = []

    model_config = {"from_attributes": True}


class TestVariantResponse(BaseModel):
    """
    Схема ответа с вариантом теста
    """
    id: UUID
    test_id: UUID
    variant_code: str
    question_order: List[UUID]
    created_at: datetime

    model_config = {"from_attributes": True}

