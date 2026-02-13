"""
Question и ImageAsset модели
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class QuestionType(str, enum.Enum):
    """
    Типы вопросов
    """
    TEXT = "text"  # Текстовый открытый вопрос
    IMAGE_ANNOTATION = "image_annotation"  # Графическая аннотация
    CHOICE = "choice"  # Тестовый вопрос (выбор варианта)


class Question(Base):
    """
    Модель вопроса
    """
    __tablename__ = "questions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    type = Column(Enum(QuestionType), nullable=False, index=True)
    content = Column(Text, nullable=False)  # Текст вопроса (может содержать HTML)
    
    # Тема/раздел вопроса
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id"), nullable=True, index=True)
    
    # Сложность вопроса (1-5)
    difficulty = Column(Integer, default=1, nullable=False, index=True)
    
    # Эталонные данные для оценки
    reference_data = Column(JSONB, nullable=True)  # Эталонный ответ или аннотации
    
    # Критерии оценки
    scoring_criteria = Column(JSONB, nullable=True)  # Веса критериев, пороги и т.д.
    
    # Флаги анти-чита
    ai_check_enabled = Column(Boolean, default=False, server_default='false', nullable=False)
    plagiarism_check_enabled = Column(Boolean, default=False, server_default='false', nullable=False)
    event_log_check_enabled = Column(Boolean, default=False, server_default='false', nullable=False)
    
    # Связь с изображением (для image_annotation вопросов)
    image_id = Column(UUID(as_uuid=True), ForeignKey("image_assets.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    author = relationship("User", back_populates="created_questions")
    topic = relationship("Topic", back_populates="questions")
    image = relationship("ImageAsset", back_populates="questions")
    test_questions = relationship("TestQuestion", back_populates="question")
    
    def __repr__(self):
        return f"<Question {self.id} ({self.type})>"


class ImageAsset(Base):
    """
    Модель для хранения изображений и их аннотаций
    """
    __tablename__ = "image_assets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    filename = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)  # Путь в MinIO/S3
    
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    file_size = Column(Integer, nullable=False)  # Размер в байтах
    
    # COCO аннотации (эталонные)
    coco_annotations = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    questions = relationship("Question", back_populates="image")
    
    def __repr__(self):
        return f"<ImageAsset {self.filename}>"

