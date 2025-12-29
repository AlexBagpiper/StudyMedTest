"""
Questions endpoints
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.storage import storage_service
from app.models.user import User, Role
from app.models.question import Question, ImageAsset, QuestionType
from app.schemas.question import QuestionCreate, QuestionUpdate, QuestionResponse, ImageAssetResponse
import io
from PIL import Image

router = APIRouter()


@router.get("/", response_model=List[QuestionResponse])
async def list_questions(
    skip: int = 0,
    limit: int = 100,
    type: QuestionType = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Список вопросов
    """
    if current_user.role == Role.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students cannot view questions"
        )
    
    query = select(Question)
    
    # Teacher видит только свои вопросы
    if current_user.role == Role.TEACHER:
        query = query.where(Question.author_id == current_user.id)
    
    if type:
        query = query.where(Question.type == type)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    questions = result.scalars().all()
    
    return questions


@router.post("/", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_question(
    question_in: QuestionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Создание вопроса (teacher, admin)
    """
    if current_user.role not in [Role.TEACHER, Role.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    question = Question(
        author_id=current_user.id,
        type=question_in.type,
        title=question_in.title,
        content=question_in.content,
        reference_data=question_in.reference_data,
        scoring_criteria=question_in.scoring_criteria,
        image_id=question_in.image_id,
    )
    
    db.add(question)
    await db.commit()
    await db.refresh(question)
    
    return question


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(
    question_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение вопроса по ID
    """
    result = await db.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    # Проверка прав доступа
    if current_user.role == Role.TEACHER and question.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return question


@router.put("/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: UUID,
    question_update: QuestionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Обновление вопроса
    """
    result = await db.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    # Проверка прав доступа
    if current_user.role == Role.TEACHER and question.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    update_data = question_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(question, field, value)
    
    await db.commit()
    await db.refresh(question)
    
    return question


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Удаление вопроса
    """
    result = await db.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    # Проверка прав доступа
    if current_user.role == Role.TEACHER and question.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    await db.delete(question)
    await db.commit()
    
    return None


@router.post("/images", response_model=ImageAssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Загрузка изображения для вопроса
    """
    if current_user.role not in [Role.TEACHER, Role.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Проверка типа файла
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Чтение и валидация изображения
    content = await file.read()
    try:
        img = Image.open(io.BytesIO(content))
        width, height = img.size
        
        # Проверка размеров
        from app.core.config import settings
        if width > settings.MAX_IMAGE_DIMENSION or height > settings.MAX_IMAGE_DIMENSION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image dimensions exceed maximum of {settings.MAX_IMAGE_DIMENSION}px"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image file: {str(e)}"
        )
    
    # Загрузка в MinIO
    import uuid
    object_name = f"images/{uuid.uuid4()}.{file.filename.split('.')[-1]}"
    
    file_data = io.BytesIO(content)
    storage_path = storage_service.upload_file(
        file_data,
        object_name,
        content_type=file.content_type
    )
    
    # Создание записи в БД
    image_asset = ImageAsset(
        filename=file.filename,
        storage_path=storage_path,
        width=width,
        height=height,
        file_size=len(content),
    )
    
    db.add(image_asset)
    await db.commit()
    await db.refresh(image_asset)
    
    return image_asset


@router.get("/images/{image_id}", response_model=ImageAssetResponse)
async def get_image(
    image_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение информации об изображении с presigned URL
    """
    result = await db.execute(select(ImageAsset).where(ImageAsset.id == image_id))
    image = result.scalar_one_or_none()
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    # Генерация presigned URL
    presigned_url = storage_service.get_presigned_url(
        image.storage_path.split("/", 1)[1],  # Убираем bucket из пути
        expires_seconds=3600
    )
    
    response = ImageAssetResponse.model_validate(image)
    response.presigned_url = presigned_url
    
    return response

