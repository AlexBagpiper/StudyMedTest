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
        # Find the submission from the logs: 9797bc0d-6dd0-42a0-9494-d46c6dd18872
        sub_id = UUID('9797bc0d-6dd0-42a0-9494-d46c6dd18872')
        res = await s.execute(select(Submission).where(Submission.id == sub_id))
        sub = res.scalar_one_or_none()
        if sub:
            print(f"ID: {sub.id}, Status: {sub.status}, Result: {sub.result}")
        else:
            print(f"Submission {sub_id} not found")

if __name__ == "__main__":
    asyncio.run(check())
