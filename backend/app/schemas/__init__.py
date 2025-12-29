"""
Pydantic схемы для валидации и сериализации
"""

from app.schemas.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserInDB,
    UserResponse,
    Token,
    TokenPayload,
)
from app.schemas.question import (
    QuestionBase,
    QuestionCreate,
    QuestionUpdate,
    QuestionResponse,
    ImageAssetResponse,
)
from app.schemas.test import (
    TestBase,
    TestCreate,
    TestUpdate,
    TestResponse,
    TestVariantResponse,
)
from app.schemas.submission import (
    SubmissionCreate,
    SubmissionResponse,
    AnswerCreate,
    AnswerUpdate,
    AnswerResponse,
)

__all__ = [
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserInDB",
    "UserResponse",
    "Token",
    "TokenPayload",
    "QuestionBase",
    "QuestionCreate",
    "QuestionUpdate",
    "QuestionResponse",
    "ImageAssetResponse",
    "TestBase",
    "TestCreate",
    "TestUpdate",
    "TestResponse",
    "TestVariantResponse",
    "SubmissionCreate",
    "SubmissionResponse",
    "AnswerCreate",
    "AnswerUpdate",
    "AnswerResponse",
]

