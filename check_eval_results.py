
import asyncio
from uuid import UUID
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.audit import AuditLog
from app.models.submission import Submission, Answer

async def check_submission_eval():
    async with AsyncSessionLocal() as session:
        # Get the most recent submission with paste events
        result = await session.execute(
            select(AuditLog).where(AuditLog.action == "submission.paste_attempted").order_by(AuditLog.timestamp.desc()).limit(1)
        )
        event = result.scalar_one_or_none()
        if not event:
            print("No paste events found.")
            return
        
        submission_id = event.resource_id
        print(f"Checking submission: {submission_id}")
        
        result = await session.execute(
            select(Submission).where(Submission.id == submission_id)
        )
        sub = result.scalar_one_or_none()
        if not sub:
            print(f"Submission {submission_id} not found.")
            return
        
        print(f"Status: {sub.status}, Result: {sub.result}")
        
        result = await session.execute(
            select(Answer).where(Answer.submission_id == submission_id)
        )
        answers = result.scalars().all()
        for ans in answers:
            print(f"Answer for Question {ans.question_id}:")
            print(f"  Score: {ans.score}")
            print(f"  Evaluation: {ans.evaluation}")

if __name__ == "__main__":
    asyncio.run(check_submission_eval())
