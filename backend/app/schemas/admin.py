"""
Admin Pydantic схемы
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import Role
from app.models.question import QuestionType
from app.models.test import TestStatus
from app.models.submission import SubmissionStatus
from app.schemas.topic import TopicResponse


T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """Пагинированный ответ"""
    items: List[T]
    total: int
    skip: int
    limit: int


class EntityCounts(BaseModel):
    """Количество пользователей по ролям"""
    total: int
    students: int
    teachers: int
    admins: int


class AdminStatsResponse(BaseModel):
    """Статистика для дашборда админа"""
    users: EntityCounts
    questions_count: int
    tests_count: int
    published_tests_count: int
    submissions_count: int
    completed_submissions_count: int
    images_count: int


# ==================== USERS ====================

class AdminUserCreate(BaseModel):
    """Создание пользователя админом"""
    email: EmailStr
    password: str = Field(..., min_length=6)
    last_name: str = Field(..., min_length=1, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    role: Role = Role.STUDENT
    is_active: bool = True
    is_verified: bool = False


class AdminUserUpdate(BaseModel):
    """Обновление пользователя админом"""
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    role: Optional[Role] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class AdminUserResponse(BaseModel):
    """Ответ с данными пользователя для админа"""
    id: UUID
    email: str
    last_name: str
    first_name: str
    middle_name: Optional[str] = None
    role: Role
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ==================== QUESTIONS ====================

class AdminQuestionUpdate(BaseModel):
    """Обновление вопроса админом"""
    content: Optional[str] = None
    type: Optional[QuestionType] = None
    reference_data: Optional[Dict[str, Any]] = None
    scoring_criteria: Optional[Dict[str, Any]] = None
    image_id: Optional[UUID] = None
    author_id: Optional[UUID] = None  # Можно сменить автора


class AdminQuestionAuthor(BaseModel):
    """Краткая информация об авторе"""
    id: UUID
    email: str
    last_name: str
    first_name: str

    model_config = {"from_attributes": True}


class AdminImageAssetBrief(BaseModel):
    """Краткая информация об изображении"""
    id: UUID
    filename: str
    storage_path: str
    width: int
    height: int

    model_config = {"from_attributes": True}


class AdminQuestionResponse(BaseModel):
    """Ответ с данными вопроса для админа"""
    id: UUID
    author_id: UUID
    author: Optional[AdminQuestionAuthor] = None
    type: QuestionType
    content: str
    topic_id: Optional[UUID] = None
    topic: Optional[TopicResponse] = None
    reference_data: Optional[Dict[str, Any]] = None
    scoring_criteria: Optional[Dict[str, Any]] = None
    image_id: Optional[UUID] = None
    image: Optional[AdminImageAssetBrief] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ==================== TESTS ====================

class AdminTestUpdate(BaseModel):
    """Обновление теста админом"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    status: Optional[TestStatus] = None
    author_id: Optional[UUID] = None  # Можно сменить автора


class AdminTestResponse(BaseModel):
    """Ответ с данными теста для админа"""
    id: UUID
    author_id: UUID
    author: Optional[AdminQuestionAuthor] = None
    title: str
    description: Optional[str] = None
    settings: Dict[str, Any]
    status: TestStatus
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ==================== SUBMISSIONS ====================

class AdminSubmissionStudent(BaseModel):
    """Информация о студенте в submission"""
    id: UUID
    email: str
    last_name: str
    first_name: str
    middle_name: Optional[str] = None

    model_config = {"from_attributes": True}


class AdminSubmissionTest(BaseModel):
    """Информация о тесте в submission"""
    id: UUID
    title: str
    author: Optional[AdminQuestionAuthor] = None

    model_config = {"from_attributes": True}


class AdminSubmissionVariant(BaseModel):
    """Информация о варианте в submission"""
    id: UUID
    variant_code: str
    test: Optional[AdminSubmissionTest] = None

    model_config = {"from_attributes": True}


class AdminAnswerResponse(BaseModel):
    """Ответ на вопрос для админа"""
    id: UUID
    question_id: UUID
    student_answer: Optional[str] = None
    annotation_data: Optional[Dict[str, Any]] = None
    evaluation: Optional[Dict[str, Any]] = None
    score: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminSubmissionResponse(BaseModel):
    """Ответ с данными submission для админа"""
    id: UUID
    student_id: UUID
    student: Optional[AdminSubmissionStudent] = None
    variant_id: UUID
    variant: Optional[AdminSubmissionVariant] = None
    status: SubmissionStatus
    started_at: datetime
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    is_hidden: bool = False
    result: Optional[Dict[str, Any]] = None
    answers: Optional[List[AdminAnswerResponse]] = None

    model_config = {"from_attributes": True}


# ==================== IMAGES ====================

class AdminImageAssetResponse(BaseModel):
    """Ответ с данными изображения для админа"""
    id: UUID
    filename: str
    storage_path: str
    width: int
    height: int
    file_size: int
    coco_annotations: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ==================== AUDIT LOGS ====================

class AdminAuditLogUser(BaseModel):
    """Краткая информация о пользователе в audit log"""
    id: UUID
    email: str

    model_config = {"from_attributes": True}


class AdminAuditLogResponse(BaseModel):
    """Ответ с данными audit log для админа"""
    id: UUID
    user_id: Optional[UUID] = None
    user: Optional[AdminAuditLogUser] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[UUID] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime

    model_config = {"from_attributes": True}


# ==================== SYSTEM CONFIGS ====================

class AdminSystemConfigUpdate(BaseModel):
    """Обновление системной настройки"""
    value: Any
    description: Optional[str] = None


class AdminSystemConfigResponse(BaseModel):
    """Ответ с системной настройкой"""
    id: UUID
    key: str
    value: Any
    description: Optional[str] = None

    model_config = {"from_attributes": True}

class AdminCVConfig(BaseModel):
    """Специальная схема для настроек CV"""
    iou_weight: float = Field(0.5, ge=0.0, le=1.0)
    recall_weight: float = Field(0.3, ge=0.0, le=1.0)
    precision_weight: float = Field(0.2, ge=0.0, le=1.0)
    iou_threshold: float = Field(0.5, ge=0.0, le=1.0)

class AdminLLMConfig(BaseModel):
    """Схема для настроек LLM"""
    yandex_api_key: Optional[str] = Field(None, description="API ключ Yandex Cloud")
    yandex_folder_id: Optional[str] = Field(None, description="ID каталога Yandex Cloud")
    yandex_model: str = Field("yandexgpt-lite/latest", description="Модель YandexGPT (yandexgpt/latest или yandexgpt-lite/latest)")
    local_llm_enabled: bool = Field(False, description="Включить локальную модель")
    local_llm_url: Optional[str] = Field(None, description="URL локального сервера (vLLM/Ollama)")
    local_llm_model: Optional[str] = Field(None, description="Название модели")
    strategy: str = Field("yandex", description="Стратегия: yandex, local, hybrid")
    fallback_enabled: bool = Field(True, description="Включить запасной вариант при ошибке")
    evaluation_prompt: Optional[str] = Field(None, description="Кастомный промпт для оценки")

    @field_validator("yandex_api_key")
    @classmethod
    def validate_yandex_api_key(cls, v: Optional[str]) -> Optional[str]:
        if v and not (v.startswith("AQVN") or v.startswith("t1.")):
            # Мы не выбрасываем ValueError, чтобы не блокировать сохранение, если пользователь уверен,
            # но в данном контексте лучше просто добавить лог или оставить как есть.
            # Однако, для строгой валидации можно было бы выбросить ошибку.
            # Оставим пока без жесткой ошибки, так как на фронте уже есть визуальная валидация.
            pass
        return v

class AdminLLMTestResponse(BaseModel):
    """Ответ на тест LLM конфигурации"""
    status: str
    message: str
    provider: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
