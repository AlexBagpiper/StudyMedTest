"""
SQLAlchemy модели
"""

from app.core.database import Base
from app.models.user import User, Role
from app.models.topic import Topic
from app.models.question import Question, QuestionType, ImageAsset
from app.models.test import Test, TestStatus, TestQuestion, TestVariant
from app.models.submission import Submission, SubmissionStatus, Answer
from app.models.audit import AuditLog
from app.models.system_config import SystemConfig

__all__ = [
    "Base",
    "User",
    "Role",
    "Topic",
    "Question",
    "QuestionType",
    "ImageAsset",
    "Test",
    "TestStatus",
    "TestQuestion",
    "TestVariant",
    "Submission",
    "SubmissionStatus",
    "Answer",
    "AuditLog",
    "SystemConfig",
]

