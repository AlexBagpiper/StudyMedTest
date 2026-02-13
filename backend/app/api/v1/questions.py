import hashlib
import json
import io
import uuid
import os
import colorsys
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from PIL import Image

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.storage import storage_service
from app.models.user import User, Role
from app.models.question import Question, ImageAsset, QuestionType
from app.models.test import TestQuestion
from app.models.submission import Answer
from app.schemas.question import QuestionCreate, QuestionUpdate, QuestionResponse, ImageAssetResponse
from app.schemas.annotation import AnnotationData

router = APIRouter()


@router.get("", response_model=List[QuestionResponse])
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
    
    query = select(Question).join(User, Question.author_id == User.id).options(
        selectinload(Question.topic),
        selectinload(Question.image),
        selectinload(Question.author)
    )
    
    # Teacher видит свои вопросы + вопросы администраторов
    if current_user.role == Role.TEACHER:
        query = query.where(
            (Question.author_id == current_user.id) | (User.role == Role.ADMIN)
        )
    
    if type:
        query = query.where(Question.type == type)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    questions = result.scalars().all()
    
    # Генерация presigned URLs для всех вопросов с изображениями
    for question in questions:
        if question.image:
            question.image.presigned_url = storage_service.get_presigned_url(
                question.image.storage_path.split("/", 1)[1],
                expires_seconds=3600
            )
        
    # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Скрываем только контуры от студентов, оставляя метки
    if current_user.role == Role.STUDENT:
        def clean_data(data):
            if not data: return data
            is_string = False
            if isinstance(data, str) and data.strip().startswith('{'):
                try:
                    data = json.loads(data)
                    is_string = True
                except: pass
            
            if isinstance(data, dict):
                cleaned = {k: clean_data(v) if isinstance(v, (dict, list)) else v 
                          for k, v in data.items() if k not in ["annotations", "segmentation", "scoring_criteria"]}
                return json.dumps(cleaned) if is_string else cleaned
            elif isinstance(data, list):
                return [clean_data(item) if isinstance(item, (dict, list)) else item for item in data]
            return data

        cleaned_questions = []
        for question in questions:
            resp_obj = QuestionResponse.model_validate(question)
            if resp_obj.reference_data:
                resp_obj.reference_data = clean_data(resp_obj.reference_data)
            if resp_obj.image and resp_obj.image.coco_annotations:
                resp_obj.image.coco_annotations = clean_data(resp_obj.image.coco_annotations)
            resp_obj.scoring_criteria = None
            cleaned_questions.append(resp_obj)
        return cleaned_questions
    
    return questions


@router.post("", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
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
    
    question_data = question_in.model_dump(mode='json')
    
    question = Question(
        author_id=current_user.id,
        type=question_in.type,
        content=question_in.content,
        topic_id=question_in.topic_id,
        difficulty=question_in.difficulty,
        reference_data=question_data.get("reference_data"),
        scoring_criteria=question_data.get("scoring_criteria"),
        ai_check_enabled=question_in.ai_check_enabled,
        plagiarism_check_enabled=question_in.plagiarism_check_enabled,
        event_log_check_enabled=question_in.event_log_check_enabled,
        image_id=question_in.image_id,
    )
    
    db.add(question)
    await db.commit()
    
    # Получаем созданный вопрос со всеми связями для ответа
    result = await db.execute(
        select(Question)
        .options(selectinload(Question.topic), selectinload(Question.image), selectinload(Question.author))
        .where(Question.id == question.id)
    )
    question = result.scalar_one()
    
    if question.image:
        question.image.presigned_url = storage_service.get_presigned_url(
            question.image.storage_path.split("/", 1)[1],
            expires_seconds=3600
        )
    
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
    result = await db.execute(
        select(Question)
        .options(selectinload(Question.topic), selectinload(Question.image), selectinload(Question.author))
        .where(Question.id == question_id)
    )
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    # Проверка прав доступа: Teacher может видеть свои или админские вопросы
    if current_user.role == Role.TEACHER:
        # Нам нужно проверить роль автора вопроса
        author_result = await db.execute(select(User.role).where(User.id == question.author_id))
        author_role = author_result.scalar_one_or_none()
        
        if question.author_id != current_user.id and author_role != Role.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
    
    if question.image:
        question.image.presigned_url = storage_service.get_presigned_url(
            question.image.storage_path.split("/", 1)[1],
            expires_seconds=3600
        )
    
    # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Скрываем только контуры от студентов, оставляя метки
    if current_user.role == Role.STUDENT:
        resp_obj = QuestionResponse.model_validate(question)
        
        def clean_data(data):
            if not data: return data
            # Если это строка (JSON), парсим её
            is_string = False
            if isinstance(data, str) and data.strip().startswith('{'):
                try:
                    data = json.loads(data)
                    is_string = True
                except: pass
            
            if isinstance(data, dict):
                # Рекурсивно удаляем 'annotations' и 'segmentation' (COCO)
                cleaned = {k: clean_data(v) if isinstance(v, (dict, list)) else v 
                          for k, v in data.items() if k not in ["annotations", "segmentation", "scoring_criteria"]}
                return json.dumps(cleaned) if is_string else cleaned
            elif isinstance(data, list):
                return [clean_data(item) if isinstance(item, (dict, list)) else item for item in data]
            return data

        if resp_obj.reference_data:
            resp_obj.reference_data = clean_data(resp_obj.reference_data)
            
        if resp_obj.image and resp_obj.image.coco_annotations:
            resp_obj.image.coco_annotations = clean_data(resp_obj.image.coco_annotations)
            
        resp_obj.scoring_criteria = None
        return resp_obj
    
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
        if field in ['reference_data', 'scoring_criteria'] and value is not None:
            # Конвертируем только JSONB поля в JSON-совместимый вид
            value = json.loads(json.dumps(value, default=str))
        setattr(question, field, value)
    
    await db.commit()
    
    # Получаем обновленный вопрос со всеми связями
    result = await db.execute(
        select(Question)
        .options(selectinload(Question.topic), selectinload(Question.image), selectinload(Question.author))
        .where(Question.id == question_id)
    )
    question = result.scalar_one()
    
    if question.image:
        question.image.presigned_url = storage_service.get_presigned_url(
            question.image.storage_path.split("/", 1)[1],
            expires_seconds=3600
        )
        
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
    
    # Проверка зависимостей
    from sqlalchemy import func
    test_count = await db.scalar(
        select(func.count(TestQuestion.id)).where(TestQuestion.question_id == question_id)
    )
    if test_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить вопрос: он используется в тестах"
        )

    answer_count = await db.scalar(
        select(func.count(Answer.id)).where(Answer.question_id == question_id)
    )
    if answer_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить вопрос: на него уже есть ответы студентов"
        )
    
    await db.delete(question)
    await db.commit()
    
    return None


@router.post("/{question_id}/duplicate", response_model=QuestionResponse)
async def duplicate_question(
    question_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Создание дубликата вопроса (текущий пользователь становится автором)
    """
    if current_user.role not in [Role.TEACHER, Role.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    # 1. Получаем исходный вопрос со всеми связями
    result = await db.execute(
        select(Question)
        .options(selectinload(Question.topic), selectinload(Question.image), selectinload(Question.author))
        .where(Question.id == question_id)
    )
    original_question = result.scalar_one_or_none()

    if not original_question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )

    # 2. Проверка прав: Teacher может дублировать свои или админские вопросы
    if current_user.role == Role.TEACHER:
        if original_question.author_id != current_user.id and original_question.author.role != Role.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to duplicate this question"
            )

    # 3. Создаем новый вопрос
    new_question = Question(
        author_id=current_user.id,
        type=original_question.type,
        content=f"{original_question.content} (копия)",
        topic_id=original_question.topic_id,
        difficulty=original_question.difficulty,
        reference_data=original_question.reference_data.copy() if isinstance(original_question.reference_data, dict) else original_question.reference_data,
        scoring_criteria=original_question.scoring_criteria.copy() if isinstance(original_question.scoring_criteria, dict) else original_question.scoring_criteria,
        ai_check_enabled=original_question.ai_check_enabled,
        plagiarism_check_enabled=original_question.plagiarism_check_enabled,
        event_log_check_enabled=original_question.event_log_check_enabled,
        image_id=original_question.image_id,
    )
    
    db.add(new_question)
    await db.commit()

    # 4. Возвращаем новый вопрос со всеми связями
    result = await db.execute(
        select(Question)
        .options(selectinload(Question.topic), selectinload(Question.image), selectinload(Question.author))
        .where(Question.id == new_question.id)
    )
    new_question = result.scalar_one()
    
    if new_question.image:
        new_question.image.presigned_url = storage_service.get_presigned_url(
            new_question.image.storage_path.split("/", 1)[1],
            expires_seconds=3600
        )

    return new_question


@router.put("/{question_id}/annotations", response_model=QuestionResponse)
async def update_question_annotations(
    question_id: UUID,
    annotations: AnnotationData,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Обновление эталонных аннотаций вопроса (teacher, admin)
    """
    result = await db.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    if current_user.role not in [Role.TEACHER, Role.ADMIN] or (current_user.role == Role.TEACHER and question.author_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Сохраняем как JSON в reference_data
    question.reference_data = annotations.model_dump(mode='json')
    
    await db.commit()
    await db.refresh(question)
    
    # Релоад со всеми связями для ответа
    result = await db.execute(
        select(Question)
        .options(selectinload(Question.topic), selectinload(Question.image), selectinload(Question.author))
        .where(Question.id == question_id)
    )
    question = result.scalar_one()
    if question.image:
        question.image.presigned_url = storage_service.get_presigned_url(
            question.image.storage_path.split("/", 1)[1],
            expires_seconds=3600
        )
    return question


@router.get("/{question_id}/labels", response_model=List[Dict[str, Any]])
async def get_question_labels(
    question_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение списка меток вопроса (для студента).
    Сначала ищет в reference_data, затем в coco_annotations привязанного изображения.
    """
    result = await db.execute(
        select(Question)
        .options(selectinload(Question.image))
        .where(Question.id == question_id)
    )
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    # 1. Если есть в reference_data (сохраненные через редактор)
    ref_data = question.reference_data
    # Если это строка (JSON), пытаемся распарсить
    if isinstance(ref_data, str) and ref_data.startswith('{'):
        try:
            ref_data = json.loads(ref_data)
        except:
            pass
            
    if isinstance(ref_data, dict):
        # Проверяем вложенный reference_answer
        if not ref_data.get("labels") and ref_data.get("reference_answer"):
            inner = ref_data.get("reference_answer")
            if isinstance(inner, str) and inner.startswith('{'):
                try:
                    ref_data = json.loads(inner)
                except:
                    pass
        
        if ref_data.get("labels"):
            return ref_data["labels"]
        
    # 2. Если нет в reference_data, берем категории из COCO аннотаций изображения
    if question.image and question.image.coco_annotations:
        coco = question.image.coco_annotations
        # Если это строка, парсим
        if isinstance(coco, str) and coco.startswith('{'):
            try:
                coco = json.loads(coco)
            except:
                pass
        
        if isinstance(coco, dict):
            categories = coco.get("categories", [])
            # Приводим к формату {id, name, color}
            labels = []

            for i, cat in enumerate(categories):
                # Генерируем максимально различные цвета с помощью золотого угла
                hue = (i * 137.508) / 360.0
                # Конвертируем HSL в RGB, затем в HEX
                r, g, b = colorsys.hls_to_rgb(hue, 0.45, 0.75)
                color = "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))
                
                name = cat.get("name", "Unknown")
                labels.append({
                    "id": str(cat.get("id")),
                    "name": name,
                    "color": color
                })
            return labels

    return []

    return []


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
    
    # Генерация presigned URL для ответа
    presigned_url = storage_service.get_presigned_url(
        image_asset.storage_path.split("/", 1)[1],
        expires_seconds=3600
    )
    
    response = ImageAssetResponse.model_validate(image_asset)
    response.presigned_url = presigned_url
    
    return response


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


def parse_coco_for_image(coco_data: dict, filename: str) -> dict:
    """
    Парсит COCO данные и оставляет только те, что относятся к конкретному изображению.
    """
    # 1. Находим изображение в 'images'
    target_image = None
    
    # Сначала ищем по точному совпадению file_name
    for img in coco_data.get('images', []):
        if img.get('file_name') == filename:
            target_image = img
            break
    
    # Если не нашли, ищем по базовому имени файла (без пути)
    if not target_image:
        base_filename = os.path.basename(filename)
        for img in coco_data.get('images', []):
            if os.path.basename(img.get('file_name', '')) == base_filename:
                target_image = img
                break
                
    if not target_image:
        return None
        
    image_id = target_image.get('id')
    
    # 2. Фильтруем аннотации
    relevant_annotations = [
        ann for ann in coco_data.get('annotations', [])
        if ann.get('image_id') == image_id
    ]
    
    # 3. Сохраняем все категории (согласно требованию)
    all_categories = coco_data.get('categories', [])
    
    return {
        "images": [target_image],
        "annotations": relevant_annotations,
        "categories": all_categories
    }


@router.post("/images/{image_id}/annotations", response_model=ImageAssetResponse)
async def upload_annotations(
    image_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Загрузка файла аннотаций для существующего изображения
    """
    if current_user.role not in [Role.TEACHER, Role.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # 1. Ищем изображение
    result = await db.execute(select(ImageAsset).where(ImageAsset.id == image_id))
    image_asset = result.scalar_one_or_none()
    
    if not image_asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    # 2. Валидация JSON
    if not file.filename.endswith(".json"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Annotations file must be a JSON file"
        )
    
    try:
        content = await file.read()
        coco_data = json.loads(content)
        
        # 3. Парсинг и проверка соответствия
        parsed_annotations = parse_coco_for_image(coco_data, image_asset.filename)
        
        if not parsed_annotations:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No annotations found for image '{image_asset.filename}' in the provided file. "
                       f"Make sure 'file_name' in JSON matches the uploaded image name."
            )
            
        # 4. Обновление в БД
        image_asset.coco_annotations = parsed_annotations
        await db.commit()
        await db.refresh(image_asset)
        
        # Генерация presigned URL для ответа
        presigned_url = storage_service.get_presigned_url(
            image_asset.storage_path.split("/", 1)[1],
            expires_seconds=3600
        )
        
        response = ImageAssetResponse.model_validate(image_asset)
        response.presigned_url = presigned_url
        
        return response
        
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON in annotations file"
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error processing annotations: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing annotations: {str(e)}"
        )
