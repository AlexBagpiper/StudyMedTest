"""
Topic модель для организации вопросов по темам
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Topic(Base):
    """
    Модель темы/раздела для вопросов
    """
    __tablename__ = "topics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Автор темы (обычно admin или teacher)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = relationship("User", back_populates="created_topics")
    questions = relationship("Question", back_populates="topic")
    
    def __repr__(self):
        return f"<Topic {self.name}>"
