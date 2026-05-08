"""
Maintenance tasks for system cleanup and rotation.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import delete

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.audit import AuditLog
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

def run_async(coro):
    """Helper to run async code in sync context (Celery worker)."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(coro)
    else:
        return loop.run_until_complete(coro)

@celery_app.task(name="maintenance.rotate_audit_logs")
def rotate_audit_logs_task():
    """
    Deletes audit logs older than settings.AUDIT_LOG_RETENTION_DAYS.
    """
    async def _rotate():
        days = settings.AUDIT_LOG_RETENTION_DAYS
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        async with AsyncSessionLocal() as db:
            try:
                stmt = delete(AuditLog).where(AuditLog.timestamp < cutoff)
                result = await db.execute(stmt)
                await db.commit()
                
                deleted_count = result.rowcount
                if deleted_count > 0:
                    logger.info(f"Rotated audit logs: deleted {deleted_count} entries older than {days} days (cutoff: {cutoff})")
                else:
                    logger.info(f"Audit log rotation: no entries older than {days} days found.")
                    
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to rotate audit logs: {e}")
                raise e

    run_async(_rotate())
