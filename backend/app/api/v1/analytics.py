"""
Analytics endpoints
"""

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, Role
from app.models.test import Test
from app.models.submission import Submission, SubmissionStatus
from app.models.question import Question

router = APIRouter()


@router.get("/teacher", response_model=Dict[str, Any])
async def get_teacher_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Аналитика для преподавателя
    """
    if current_user.role not in [Role.TEACHER, Role.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Статистика по тестам преподавателя
    query = select(Test).where(Test.author_id == current_user.id)
    result = await db.execute(query)
    tests = result.scalars().all()
    
    total_tests = len(tests)
    published_tests = len([t for t in tests if t.status == "published"])
    draft_tests = len([t for t in tests if t.status == "draft"])
    
    # Статистика по вопросам
    result = await db.execute(
        select(func.count(Question.id)).where(Question.author_id == current_user.id)
    )
    total_questions = result.scalar()
    
    # Статистика по submissions
    # Получаем все submissions для тестов преподавателя
    from app.models.test import TestVariant
    
    result = await db.execute(
        select(func.count(Submission.id))
        .join(TestVariant)
        .join(Test)
        .where(Test.author_id == current_user.id)
    )
    total_submissions = result.scalar()
    
    result = await db.execute(
        select(func.count(Submission.id))
        .join(TestVariant)
        .join(Test)
        .where(
            Test.author_id == current_user.id,
            Submission.status == SubmissionStatus.COMPLETED
        )
    )
    completed_submissions = result.scalar()
    
    return {
        "tests": {
            "total": total_tests,
            "published": published_tests,
            "draft": draft_tests,
        },
        "questions": {
            "total": total_questions,
        },
        "submissions": {
            "total": total_submissions,
            "completed": completed_submissions,
        }
    }


@router.get("/admin", response_model=Dict[str, Any])
async def get_admin_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Расширенная аналитика для администратора
    """
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # Пользователи
    result = await db.execute(select(func.count(User.id)))
    total_users = result.scalar()
    
    result = await db.execute(
        select(func.count(User.id)).where(User.role == Role.STUDENT)
    )
    total_students = result.scalar()
    
    result = await db.execute(
        select(func.count(User.id)).where(User.role == Role.TEACHER)
    )
    total_teachers = result.scalar()
    
    # Тесты
    result = await db.execute(select(func.count(Test.id)))
    total_tests = result.scalar()
    
    result = await db.execute(
        select(func.count(Test.id)).where(Test.status == "published")
    )
    published_tests = result.scalar()
    
    # Вопросы
    result = await db.execute(select(func.count(Question.id)))
    total_questions = result.scalar()
    
    # Submissions
    result = await db.execute(select(func.count(Submission.id)))
    total_submissions = result.scalar()
    
    result = await db.execute(
        select(func.count(Submission.id))
        .where(Submission.status == SubmissionStatus.COMPLETED)
    )
    completed_submissions = result.scalar()
    
    # Средний балл (из completed submissions)
    result = await db.execute(
        select(Submission)
        .where(Submission.status == SubmissionStatus.COMPLETED)
    )
    submissions = result.scalars().all()
    
    if submissions:
        scores = [
            s.result.get("percentage", 0)
            for s in submissions
            if s.result and "percentage" in s.result
        ]
        average_score = sum(scores) / len(scores) if scores else 0
    else:
        average_score = 0
    
    return {
        "users": {
            "total": total_users,
            "students": total_students,
            "teachers": total_teachers,
        },
        "tests": {
            "total": total_tests,
            "published": published_tests,
        },
        "questions": {
            "total": total_questions,
        },
        "submissions": {
            "total": total_submissions,
            "completed": completed_submissions,
            "average_score": round(average_score, 2),
        }
    }


@router.get("/test/{test_id}", response_model=Dict[str, Any])
async def get_test_analytics(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Аналитика по конкретному тесту
    """
    # Проверка теста
    result = await db.execute(select(Test).where(Test.id == test_id))
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    # Проверка прав доступа
    if current_user.role == Role.TEACHER and test.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Получение submissions для этого теста
    from app.models.test import TestVariant
    
    result = await db.execute(
        select(Submission)
        .join(TestVariant)
        .where(TestVariant.test_id == test_id)
    )
    submissions = result.scalars().all()
    
    total_attempts = len(submissions)
    completed = len([s for s in submissions if s.status == SubmissionStatus.COMPLETED])
    in_progress = len([s for s in submissions if s.status == SubmissionStatus.IN_PROGRESS])
    
    # Распределение баллов
    scores = [
        s.result.get("percentage", 0)
        for s in submissions
        if s.status == SubmissionStatus.COMPLETED and s.result
    ]
    
    if scores:
        avg_score = sum(scores) / len(scores)
        min_score = min(scores)
        max_score = max(scores)
    else:
        avg_score = min_score = max_score = 0
    
    return {
        "test_id": str(test_id),
        "test_title": test.title,
        "attempts": {
            "total": total_attempts,
            "completed": completed,
            "in_progress": in_progress,
        },
        "scores": {
            "average": round(avg_score, 2),
            "min": round(min_score, 2),
            "max": round(max_score, 2),
        },
        "distribution": scores,
    }

