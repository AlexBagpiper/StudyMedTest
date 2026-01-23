import asyncio
import sys
import os
from uuid import UUID

# Добавляем путь к приложению
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import AsyncSessionLocal
from app.models.submission import Submission, Answer

async def check_submission():
    sid = UUID('b3200903-4cbf-4e0d-a68f-6b816dd3f646')
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Submission)
            .options(selectinload(Submission.answers))
            .where(Submission.id == sid)
        )
        sub = result.scalar_one_or_none()
        if sub:
            print(f"Submission ID: {sub.id}")
            print(f"Status: {sub.status}")
            print(f"Answers count: {len(sub.answers)}")
            for i, ans in enumerate(sub.answers):
                print(f"  Answer {i}: Q={ans.question_id}, Score={ans.score}")
        else:
            print("Submission not found")

if __name__ == "__main__":
    asyncio.run(check_submission())
