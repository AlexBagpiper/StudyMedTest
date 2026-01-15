"""
User модель и RBAC
"""

import enum
import uuid
from datetime import datetime
from typing import List

from sqlalchemy import Boolean, Column, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Role(str, enum.Enum):
    """
    Роли пользователей
    """
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


# RBAC Permissions
PERMISSIONS = {
    "admin": ["*"],  # Все права
    "teacher": [
        "question:create",
        "question:read_own",
        "question:update_own",
        "question:delete_own",
        "test:create",
        "test:read_own",
        "test:update_own",
        "test:publish",
        "result:read_own_tests",
        "analytics:read_own",
        "student:read_list",
    ],
    "student": [
        "test:read_published",
        "test:submit",
        "result:read_own",
        "profile:read_own",
        "profile:update_own",
    ]
}


class User(Base):
    """
    Модель пользователя (Student, Teacher, Admin)
    """
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    last_name = Column(String(100), nullable=False)  # Фамилия
    first_name = Column(String(100), nullable=False)  # Имя
    middle_name = Column(String(100), nullable=True)  # Отчество (опционально)
    role = Column(Enum(Role), nullable=False, default=Role.STUDENT, index=True)
    
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Email change verification
    pending_email = Column(String(255), nullable=True)  # Новый email ожидающий подтверждения
    email_change_code = Column(String(6), nullable=True)  # 6-значный код
    email_change_expires = Column(DateTime, nullable=True)  # Срок действия кода
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    created_topics = relationship(
        "Topic",
        back_populates="creator",
        foreign_keys="Topic.created_by"
    )
    created_questions = relationship(
        "Question",
        back_populates="author",
        foreign_keys="Question.author_id"
    )
    created_tests = relationship(
        "Test",
        back_populates="author",
        foreign_keys="Test.author_id"
    )
    submissions = relationship(
        "Submission",
        back_populates="student",
        foreign_keys="Submission.student_id"
    )
    audit_logs = relationship("AuditLog", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.email} ({self.role})>"
    
    def has_permission(self, permission: str) -> bool:
        """
        Проверка наличия permission у пользователя
        """
        user_permissions = PERMISSIONS.get(self.role, [])
        return "*" in user_permissions or permission in user_permissions

