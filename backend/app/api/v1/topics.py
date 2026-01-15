"""
Topics endpoints
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, Role
from app.models.topic import Topic
from app.schemas.topic import TopicCreate, TopicUpdate, TopicResponse

router = APIRouter()


@router.get("/", response_model=List[TopicResponse])
async def list_topics(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Список тем (доступно всем авторизованным)
    """
    query = select(Topic).offset(skip).limit(limit).order_by(Topic.name)
    result = await db.execute(query)
    topics = result.scalars().all()
    
    return topics


@router.post("/", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
async def create_topic(
    topic_in: TopicCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Создание темы (teacher, admin)
    """
    if current_user.role not in [Role.TEACHER, Role.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Проверка уникальности имени
    existing = await db.execute(
        select(Topic).where(Topic.name == topic_in.name)
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Topic with this name already exists"
        )
    
    topic = Topic(
        name=topic_in.name,
        description=topic_in.description,
        created_by=current_user.id,
    )
    
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    
    return topic


@router.get("/{topic_id}", response_model=TopicResponse)
async def get_topic(
    topic_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение темы по ID
    """
    result = await db.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()
    
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found"
        )
    
    return topic


@router.put("/{topic_id}", response_model=TopicResponse)
async def update_topic(
    topic_id: UUID,
    topic_update: TopicUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Обновление темы (admin или создатель)
    """
    result = await db.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()
    
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found"
        )
    
    # Проверка прав доступа
    if current_user.role != Role.ADMIN and topic.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    update_data = topic_update.model_dump(exclude_unset=True, mode='json')
    
    # Проверка уникальности имени если меняется
    if "name" in update_data and update_data["name"] != topic.name:
        existing = await db.execute(
            select(Topic).where(Topic.name == update_data["name"])
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Topic with this name already exists"
            )
    
    for field, value in update_data.items():
        setattr(topic, field, value)
    
    await db.commit()
    await db.refresh(topic)
    
    return topic


@router.delete("/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic(
    topic_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Удаление темы (admin или создатель)
    """
    result = await db.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()
    
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found"
        )
    
    # Проверка прав доступа
    if current_user.role != Role.ADMIN and topic.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Проверка что нет вопросов с этой темой
    from app.models.question import Question
    result = await db.execute(
        select(func.count()).select_from(Question).where(Question.topic_id == topic_id)
    )
    if result.scalar() > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete topic with associated questions"
        )
    
    await db.delete(topic)
    await db.commit()
    
    return None
