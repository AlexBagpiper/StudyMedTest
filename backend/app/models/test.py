"""
Test, TestQuestion, TestVariant модели
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class TestStatus(str, enum.Enum):
    """
    Статусы теста
    """
    DRAFT = "draft"  # Черновик
    PUBLISHED = "published"  # Опубликован
    ARCHIVED = "archived"  # Архивирован


class Test(Base):
    """
    Модель теста
    """
    __tablename__ = "tests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Настройки теста
    settings = Column(JSONB, nullable=False, default={})
    # settings содержит:
    # - time_limit_minutes: int
    # - max_attempts: int
    # - shuffle_questions: bool
    # - show_results_immediately: bool
    # - passing_score: float
    
    status = Column(Enum(TestStatus), default=TestStatus.DRAFT, nullable=False, index=True)
    
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    author = relationship("User", back_populates="created_tests")
    test_questions = relationship(
        "TestQuestion",
        back_populates="test",
        cascade="all, delete-orphan",
        order_by="TestQuestion.order"
    )
    variants = relationship(
        "TestVariant",
        back_populates="test",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Test {self.title} ({self.status})>"


class TestQuestion(Base):
    """
    Связь между Test и Question (many-to-many с дополнительными полями)
    """
    __tablename__ = "test_questions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_id = Column(UUID(as_uuid=True), ForeignKey("tests.id"), nullable=False)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id"), nullable=False)
    
    order = Column(Integer, nullable=False)  # Порядок вопроса в тесте
    weight = Column(Integer, default=1, nullable=False)  # Вес вопроса для подсчёта баллов
    
    # Relationships
    test = relationship("Test", back_populates="test_questions")
    question = relationship("Question", back_populates="test_questions")
    
    def __repr__(self):
        return f"<TestQuestion test={self.test_id} question={self.question_id}>"


class TestVariant(Base):
    """
    Вариант теста (для рандомизации вопросов)
    """
    __tablename__ = "test_variants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_id = Column(UUID(as_uuid=True), ForeignKey("tests.id"), nullable=False)
    
    variant_code = Column(String(50), nullable=False, unique=True, index=True)
    
    # Порядок вопросов для этого варианта
    question_order = Column(JSONB, nullable=False)  # List[UUID] - порядок question_id
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    test = relationship("Test", back_populates="variants")
    submissions = relationship("Submission", back_populates="variant")
    
    def __repr__(self):
        return f"<TestVariant {self.variant_code}>"

