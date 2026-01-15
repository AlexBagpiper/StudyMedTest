"""
Test Pydantic схемы
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.test import TestStatus


from app.schemas.question import QuestionResponse


class TestQuestionCreate(BaseModel):
    """
    Схема для добавления вопроса в тест
    """
    question_id: UUID
    order: int


class TestQuestionResponse(BaseModel):
    """
    Схема ответа для вопроса в тесте
    """
    id: UUID
    test_id: UUID
    question_id: UUID
    order: int
    question: Optional[QuestionResponse] = None

    model_config = {"from_attributes": True}


class TestStructureItem(BaseModel):
    """
    Элемент структуры теста (правило генерации)
    """
    topic_id: UUID
    question_type: str  # text, image_annotation
    count: int = Field(..., ge=1)
    difficulty: int = Field(default=1, ge=1, le=5)


class TestBase(BaseModel):
    """
    Базовая схема теста
    """
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)
    structure: Optional[List[TestStructureItem]] = None


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
    structure: Optional[List[TestStructureItem]] = None
    questions: Optional[List[TestQuestionCreate]] = None
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
    
    test_questions: List[TestQuestionResponse] = []

    model_config = {"from_attributes": True}


class TestListResponse(TestBase):
    """
    Схема для списка тестов (без вопросов)
    """
    id: UUID
    author_id: UUID
    status: TestStatus
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

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

