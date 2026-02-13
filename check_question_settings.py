
import asyncio
from uuid import UUID
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.question import Question

async def check_question():
    async with AsyncSessionLocal() as session:
        question_id = UUID('850401f9-6435-472f-8630-6c552447434f')
        result = await session.execute(
            select(Question).where(Question.id == question_id)
        )
        q = result.scalar_one_or_none()
        if not q:
            print("Question not found")
            return
        
        print(f"Question: {q.content[:50]}...")
        print(f"event_log_check_enabled: {q.event_log_check_enabled}")
        print(f"ai_check_enabled: {q.ai_check_enabled}")

if __name__ == "__main__":
    asyncio.run(check_question())
