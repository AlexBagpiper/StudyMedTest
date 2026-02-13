
import asyncio
from uuid import UUID
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.audit import AuditLog

async def check_events():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.action.like("submission.%")).order_by(AuditLog.timestamp.desc()).limit(10)
        )
        events = result.scalars().all()
        if not events:
            print("No submission events found.")
            return
        
        for ev in events:
            print(f"Time: {ev.timestamp}, Action: {ev.action}, Details: {ev.details}")

if __name__ == "__main__":
    asyncio.run(check_events())
