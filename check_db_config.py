import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import json

# Load env from backend/.env
load_dotenv("backend/.env")

DATABASE_URL = os.getenv("DATABASE_URL")
# If DATABASE_URL uses 'db' as host (for docker), change it to 'localhost' for local access
if "postgresql+asyncpg://medtest_user:medtest_password@db:5432/medtest_db" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("@db:", "@localhost:")
elif "@db:" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("@db:", "@localhost:")

print(f"Connecting to DB: {DATABASE_URL}")

async def check_config():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        from sqlalchemy import text
        try:
            result = await session.execute(text("SELECT key, value FROM system_configs WHERE key = 'llm_evaluation_params'"))
            row = result.fetchone()
            if row:
                print(f"Config found: {row[0]}")
                print(json.dumps(row[1], indent=2, ensure_ascii=False))
            else:
                print("No LLM config found in DB.")
        except Exception as e:
            print(f"Error reading DB: {e}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_config())
