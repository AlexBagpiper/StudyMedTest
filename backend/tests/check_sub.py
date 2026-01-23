import asyncio
import sys
import os
from uuid import UUID

# Добавляем путь к приложению
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timedelta
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.submission import Submission

async def check_submission():
    sid = UUID('b3200903-4cbf-4e0d-a68f-6b816dd3f646')
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Submission).where(Submission.id == sid))
        sub = result.scalar_one_or_none()
        if sub:
            print(f"Submission ID: {sub.id}")
            print(f"Status: {sub.status}")
            print(f"Started At: {sub.started_at}")
            print(f"Current UTC: {datetime.utcnow()}")
            print(f"Is naive? {sub.started_at.tzinfo is None}")
            # ...

if __name__ == "__main__":
    asyncio.run(check_submission())
