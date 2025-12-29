"""
Tests endpoints
"""

from typing import List
from uuid import UUID
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, Role
from app.models.test import Test, TestStatus, TestQuestion, TestVariant
from app.models.question import Question
from app.schemas.test import TestCreate, TestUpdate, TestResponse, TestVariantResponse

router = APIRouter()


@router.get("/", response_model=List[TestResponse])
async def list_tests(
    skip: int = 0,
    limit: int = 100,
    status: TestStatus = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Список тестов
    """
    query = select(Test)
    
    # Students видят только опубликованные тесты
    if current_user.role == Role.STUDENT:
        query = query.where(Test.status == TestStatus.PUBLISHED)
    # Teacher видит только свои тесты
    elif current_user.role == Role.TEACHER:
        query = query.where(Test.author_id == current_user.id)
    
    if status:
        query = query.where(Test.status == status)
    
    query = query.offset(skip).limit(limit).order_by(Test.created_at.desc())
    result = await db.execute(query)
    tests = result.scalars().all()
    
    return tests


@router.post("/", response_model=TestResponse, status_code=status.HTTP_201_CREATED)
async def create_test(
    test_in: TestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Создание теста
    """
    if current_user.role not in [Role.TEACHER, Role.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    test = Test(
        author_id=current_user.id,
        title=test_in.title,
        description=test_in.description,
        settings=test_in.settings,
        status=TestStatus.DRAFT,
    )
    
    db.add(test)
    await db.flush()
    
    # Добавление вопросов
    for q in test_in.questions:
        # Проверка существования вопроса
        result = await db.execute(select(Question).where(Question.id == q.question_id))
        question = result.scalar_one_or_none()
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question {q.question_id} not found"
            )
        
        test_question = TestQuestion(
            test_id=test.id,
            question_id=q.question_id,
            order=q.order,
            weight=q.weight,
        )
        db.add(test_question)
    
    await db.commit()
    await db.refresh(test)
    
    return test


@router.get("/{test_id}", response_model=TestResponse)
async def get_test(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение теста по ID
    """
    result = await db.execute(
        select(Test)
        .options(selectinload(Test.test_questions))
        .where(Test.id == test_id)
    )
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    # Проверка прав доступа
    if current_user.role == Role.STUDENT and test.status != TestStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test not published"
        )
    
    if current_user.role == Role.TEACHER and test.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return test


@router.put("/{test_id}", response_model=TestResponse)
async def update_test(
    test_id: UUID,
    test_update: TestUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Обновление теста
    """
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
    
    update_data = test_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(test, field, value)
    
    await db.commit()
    await db.refresh(test)
    
    return test


@router.post("/{test_id}/publish", response_model=TestResponse)
async def publish_test(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Публикация теста и генерация вариантов
    """
    result = await db.execute(
        select(Test)
        .options(selectinload(Test.test_questions))
        .where(Test.id == test_id)
    )
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
    
    if test.status == TestStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test already published"
        )
    
    # Проверка наличия вопросов
    if not test.test_questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot publish test without questions"
        )
    
    # Публикация
    from datetime import datetime
    test.status = TestStatus.PUBLISHED
    test.published_at = datetime.utcnow()
    
    # Генерация варианта (можно генерировать несколько вариантов)
    question_ids = [tq.question_id for tq in test.test_questions]
    
    # Если включена рандомизация - перемешиваем вопросы
    if test.settings.get("shuffle_questions", False):
        import random
        random.shuffle(question_ids)
    
    variant = TestVariant(
        test_id=test.id,
        variant_code=secrets.token_urlsafe(8),
        question_order=question_ids,
    )
    
    db.add(variant)
    await db.commit()
    await db.refresh(test)
    
    return test


@router.get("/{test_id}/variants", response_model=List[TestVariantResponse])
async def get_test_variants(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение вариантов теста
    """
    # Проверка существования теста
    result = await db.execute(select(Test).where(Test.id == test_id))
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    # Получение вариантов
    result = await db.execute(
        select(TestVariant).where(TestVariant.test_id == test_id)
    )
    variants = result.scalars().all()
    
    return variants


@router.delete("/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Удаление теста
    """
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
    
    await db.delete(test)
    await db.commit()
    
    return None

