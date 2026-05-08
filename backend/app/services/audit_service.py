from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog
from app.core.database import get_db
import logging

logger = logging.getLogger(__name__)

class AuditService:
    @classmethod
    async def log_event(
        cls,
        db: AsyncSession,
        action: str,
        user_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Универсальный метод для логирования событий.
        """
        # Превращаем UUID в строки для JSONB если нужно, 
        # хотя SQLAlchemy обычно справляется если настроен json_serializer
        
        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.utcnow()
        )
        db.add(audit_entry)
        return audit_entry

    @classmethod
    async def log_request(
        cls,
        action: str,
        request: Request,
        db: AsyncSession,
        user_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """
        Логирование события с автоматическим извлечением IP и User-Agent из запроса FastAPI.
        """
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        return await cls.log_event(
            db=db,
            action=action,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )

audit_service = AuditService()
