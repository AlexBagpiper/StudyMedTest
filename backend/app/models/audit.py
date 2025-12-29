"""
Audit Log модель
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class AuditLog(Base):
    """
    Модель для аудита действий пользователей
    """
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    action = Column(String(100), nullable=False, index=True)
    # Примеры: "user.login", "test.publish", "answer.submit", "role.change"
    
    resource_type = Column(String(50), nullable=True)  # "test", "question", "user"
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    details = Column(JSONB, nullable=True)  # Дополнительная информация
    
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog {self.action} by user={self.user_id}>"

