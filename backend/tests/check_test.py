import asyncio
import sys
import os
from uuid import UUID

# Добавляем путь к приложению
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.test import Test, TestVariant

async def check_test():
    vid = UUID('d3e52ed1-7575-4b46-9726-969803155adb')
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Test)
            .join(TestVariant)
            .where(TestVariant.id == vid)
        )
        test = result.scalar_one_or_none()
        if test:
            print(f"Test ID: {test.id}")
            print(f"Settings: {test.settings}")
        else:
            print("Test not found")

if __name__ == "__main__":
    asyncio.run(check_test())
