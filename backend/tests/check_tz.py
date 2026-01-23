import asyncio
import sys
import os

# Добавляем путь к приложению
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def check_tz():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SHOW timezone;"))
        tz = result.scalar()
        print(f"Postgres Timezone: {tz}")
        
        result = await session.execute(text("SELECT now();"))
        now = result.scalar()
        print(f"Postgres now(): {now}")
        
        import datetime
        print(f"Python utcnow(): {datetime.datetime.utcnow()}")

if __name__ == "__main__":
    asyncio.run(check_tz())
