"""
Submission и Answer модели
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class SubmissionStatus(str, enum.Enum):
    """
    Статусы submission (прохождения теста)
    """
    IN_PROGRESS = "in_progress"  # В процессе
    SUBMITTED = "submitted"  # Отправлен
    EVALUATING = "evaluating"  # Идёт оценка (LLM/CV обработка)
    COMPLETED = "completed"  # Завершён с результатами


class Submission(Base):
    """
    Модель попытки прохождения теста студентом
    """
    __tablename__ = "submissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    variant_id = Column(UUID(as_uuid=True), ForeignKey("test_variants.id"), nullable=False)
    
    status = Column(
        Enum(SubmissionStatus),
        default=SubmissionStatus.IN_PROGRESS,
        nullable=False,
        index=True
    )
    
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    is_hidden = Column(Boolean, default=False, nullable=False)
    
    # Результаты
    result = Column(JSONB, nullable=True)
    # result содержит:
    # - total_score: float
    # - max_score: float
    # - percentage: float
    # - grade: str (например, "5", "4", "3", etc.)
    # - feedback: str (опциональная общая обратная связь от LLM)
    
    # Relationships
    student = relationship("User", back_populates="submissions")
    variant = relationship("TestVariant", back_populates="submissions")
    answers = relationship(
        "Answer",
        back_populates="submission",
        cascade="all, delete-orphan"
    )
    
    @property
    def test_id(self):
        return self.variant.test_id if self.variant else None
    
    @property
    def test_title(self):
        return self.variant.test.title if self.variant and self.variant.test else None
    
    @property
    def teacher(self):
        return self.variant.test.author if self.variant and self.variant.test else None
    
    def __repr__(self):
        return f"<Submission {self.id} ({self.status})>"


class Answer(Base):
    """
    Модель ответа на один вопрос
    """
    __tablename__ = "answers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("submissions.id"), nullable=False)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id"), nullable=False)
    
    # Ответ студента
    student_answer = Column(Text, nullable=True)  # Текстовый ответ
    annotation_data = Column(JSONB, nullable=True)  # COCO аннотации студента
    annotation_file_path = Column(Text, nullable=True)  # Путь к файлу аннотаций в S3
    
    # Оценка
    evaluation = Column(JSONB, nullable=True)
    # evaluation содержит:
    # - criteria_scores: dict (оценки по критериям)
    # - feedback: str (обратная связь)
    # - llm_provider: str (какая модель использовалась)
    # - evaluated_at: datetime
    
    score = Column(Float, nullable=True)  # Итоговый балл за вопрос
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    submission = relationship("Submission", back_populates="answers")
    question = relationship("Question")
    
    def __repr__(self):
        return f"<Answer {self.id} score={self.score}>"

