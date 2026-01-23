import asyncio
import os
import sys
from uuid import UUID

# Add current directory to path
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.submission import Submission
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as s:
        res = await s.execute(select(Submission).order_by(Submission.started_at.desc()).limit(5))
        subs = res.scalars().all()
        for sub in subs:
            print(f"ID: {sub.id}, Status: {sub.status}, Result: {sub.result}")

if __name__ == "__main__":
    asyncio.run(check())
