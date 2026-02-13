
import asyncio
from uuid import UUID
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.audit import AuditLog

async def debug_events():
    async with AsyncSessionLocal() as session:
        sub_id = UUID('f61bf5d7-175d-4c47-844a-659fcb69c5cc')
        result = await session.execute(
            select(AuditLog).where(
                AuditLog.resource_id == sub_id,
                AuditLog.action.like("submission.%")
            )
        )
        events = result.scalars().all()
        print(f"Found {len(events)} events for submission {sub_id}")
        for ev in events:
            print(f"Action: {ev.action}, Details: {ev.details}")

if __name__ == "__main__":
    asyncio.run(debug_events())
