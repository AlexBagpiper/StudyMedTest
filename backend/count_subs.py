import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.submission import Submission
from sqlalchemy import func, select

async def count():
    async with AsyncSessionLocal() as s:
        res = await s.execute(select(func.count(Submission.id)))
        print(f"Total submissions: {res.scalar()}")

if __name__ == "__main__":
    asyncio.run(count())
