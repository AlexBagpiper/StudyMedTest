from sqlalchemy import Column, String, JSON
from app.core.database import Base
from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID

class SystemConfig(Base):
    __tablename__ = "system_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(JSON, nullable=False)
    description = Column(String, nullable=True)
