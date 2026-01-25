"""
Test Pydantic схемы
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

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
    
    # Переопределяем structure для более гибкой обработки некорректных данных
    structure: Optional[List[Dict[str, Any]]] = None

    model_config = {"from_attributes": True}
    
    @model_validator(mode='before')
    @classmethod
    def validate_structure(cls, data: Any) -> Any:
        """
        Валидация с обработкой некорректных данных structure и settings
        """
        # Обработка structure
        if isinstance(data, dict):
            structure = data.get('structure')
            settings = data.get('settings')
        elif hasattr(data, 'structure'):
            structure = data.structure
            settings = getattr(data, 'settings', None)
        else:
            structure = None
            settings = None
            
        if structure is not None:
            try:
                # Если structure - это список, проверяем элементы
                if isinstance(structure, list):
                    # Преобразуем в список dict для более гибкой сериализации
                    validated_structure = []
                    for item in structure:
                        if isinstance(item, dict):
                            validated_structure.append(item)
                        elif hasattr(item, '__dict__'):
                            validated_structure.append(dict(item))
                        else:
                            # Пропускаем некорректные элементы
                            continue
                    if isinstance(data, dict):
                        data['structure'] = validated_structure if validated_structure else None
                    elif hasattr(data, '__dict__'):
                        data.structure = validated_structure if validated_structure else None
                else:
                    # Если structure не список, устанавливаем None
                    if isinstance(data, dict):
                        data['structure'] = None
                    elif hasattr(data, '__dict__'):
                        data.structure = None
            except Exception:
                # В случае любой ошибки устанавливаем None
                if isinstance(data, dict):
                    data['structure'] = None
                elif hasattr(data, '__dict__'):
                    data.structure = None
        
        # Обработка settings - убеждаемся, что это dict
        if settings is None:
            if isinstance(data, dict):
                data['settings'] = {}
            elif hasattr(data, '__dict__'):
                data.settings = {}
        elif not isinstance(settings, dict):
            # Если settings не dict, пытаемся преобразовать или устанавливаем пустой dict
            try:
                if isinstance(data, dict):
                    data['settings'] = dict(settings) if hasattr(settings, '__iter__') else {}
                elif hasattr(data, '__dict__'):
                    data.settings = dict(settings) if hasattr(settings, '__iter__') else {}
            except Exception:
                if isinstance(data, dict):
                    data['settings'] = {}
                elif hasattr(data, '__dict__'):
                    data.settings = {}
        
        return data


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

