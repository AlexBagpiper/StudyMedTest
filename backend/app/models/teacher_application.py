"""
Teacher Application модель
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class ApplicationStatus(str, enum.Enum):
    """Статусы заявки"""
    PENDING = "pending"      # Ожидает рассмотрения
    APPROVED = "approved"    # Одобрена
    REJECTED = "rejected"    # Отклонена


class TeacherApplication(Base):
    """
    Заявка на регистрацию преподавателя
    """
    __tablename__ = "teacher_applications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Данные заявителя
    email = Column(String(255), nullable=False, index=True)
    last_name = Column(String(100), nullable=False)
    first_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)
    
    # Дополнительная информация
    phone = Column(String(20), nullable=True)         # Телефон
    
    # Статус и обработка
    status = Column(
        Enum(ApplicationStatus, native_enum=False),
        nullable=False,
        default=ApplicationStatus.PENDING,
        index=True
    )
    admin_comment = Column(Text, nullable=True)  # Комментарий администратора
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    
    def __repr__(self):
        return f"<TeacherApplication {self.email} ({self.status})>"
