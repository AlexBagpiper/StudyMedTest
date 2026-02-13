"""
Tests endpoints
"""

from typing import List
from uuid import UUID
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.storage import storage_service
from app.models.user import User, Role
from app.models.test import Test, TestStatus, TestQuestion, TestVariant
from app.models.question import Question
from app.models.submission import Submission, SubmissionStatus
from app.schemas.test import TestCreate, TestUpdate, TestResponse, TestListResponse, TestVariantResponse
from app.schemas.submission import SubmissionResponse

router = APIRouter()


def populate_test_question_urls(test: Test):
    """Генерация presigned URLs для всех вопросов в тесте"""
    if not test.test_questions:
        return
    for tq in test.test_questions:
        if tq.question and tq.question.image:
            tq.question.image.presigned_url = storage_service.get_presigned_url(
                tq.question.image.storage_path.split("/", 1)[1],
                expires_seconds=3600
            )


@router.post("/{test_id}/start", response_model=SubmissionResponse)
async def start_test(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Начать прохождение теста (генерация варианта и создание submission)
    """
    # 1. Ищем тест
    result = await db.execute(select(Test).where(Test.id == test_id))
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    if test.status != TestStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test is not published"
        )
    
    # 2. Проверка, нет ли уже начатого теста (in_progress) для этого пользователя
    # Нам нужно найти все submissions студента для любого варианта этого же теста
    result = await db.execute(
        select(Submission)
        .join(TestVariant)
        .where(
            Submission.student_id == current_user.id,
            TestVariant.test_id == test_id
        )
        .order_by(Submission.attempt_number.desc())
    )
    existing_submissions = result.scalars().all()
    
    attempt_number = 1
    if existing_submissions:
        # Если есть незавершенная попытка, возвращаем её
        in_progress = next((s for s in existing_submissions if s.status == SubmissionStatus.IN_PROGRESS), None)
        if in_progress:
            # Возвращаем существующую попытку со всеми связями
            result = await db.execute(
                select(Submission)
                .options(
                    selectinload(Submission.answers),
                    joinedload(Submission.variant).joinedload(TestVariant.test).joinedload(Test.author)
                )
                .where(Submission.id == in_progress.id)
            )
            sub = result.unique().scalar_one()
            sub.time_limit = sub.variant.test.settings.get("time_limit")
            return sub

        # Если все попытки завершены, проверяем разрешение на пересдачу
        from app.models.submission import RetakePermission
        result = await db.execute(
            select(RetakePermission)
            .where(
                RetakePermission.student_id == current_user.id,
                RetakePermission.test_id == test_id,
                RetakePermission.submission_id == None  # Разрешение еще не использовано
            )
            .order_by(RetakePermission.created_at.desc())
        )
        permission = result.scalar_one_or_none()
        
        if not permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Test already submitted. Request a retake from your teacher."
            )
        
        attempt_number = existing_submissions[0].attempt_number + 1
    else:
        # Первая попытка
        attempt_number = 1

    # 3. Получение фиксированных вопросов и генерация варианта
    result = await db.execute(
        select(TestQuestion.question_id)
        .where(TestQuestion.test_id == test_id)
        .order_by(TestQuestion.order)
    )
    fixed_question_ids = [r[0] for r in result.all()]
    
    if test.structure:
        generated_ids = await generate_test_variant_questions(
            db, test.structure, exclude_ids=fixed_question_ids
        )
        question_ids = fixed_question_ids + generated_ids
    else:
        question_ids = fixed_question_ids
    
    if not question_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No questions available for this test"
        )
        
    # Convert UUIDs to strings for JSONB serialization
    question_ids_str = [str(qid) for qid in question_ids]
    
    variant = TestVariant(
        test_id=test.id,
        variant_code=secrets.token_urlsafe(8),
        question_order=question_ids_str,
    )
    db.add(variant)
    await db.flush() # Получаем ID варианта
    
    # 4. Создание submission
    submission = Submission(
        student_id=current_user.id,
        variant_id=variant.id,
        status=SubmissionStatus.IN_PROGRESS,
        attempt_number=attempt_number
    )
    db.add(submission)
    await db.flush() # Получаем ID

    # Если это пересдача по разрешению, привязываем его
    if attempt_number > 1:
        from app.models.submission import RetakePermission
        result = await db.execute(
            select(RetakePermission)
            .where(
                RetakePermission.student_id == current_user.id,
                RetakePermission.test_id == test_id,
                RetakePermission.submission_id == None
            )
            .order_by(RetakePermission.created_at.desc())
        )
        permission = result.scalar_one_or_none()
        if permission:
            permission.submission_id = submission.id

    await db.commit()
    
    # Релоад со всеми связями для ответа (нужно для SubmissionResponse)
    result = await db.execute(
        select(Submission)
        .options(
            selectinload(Submission.answers),
            joinedload(Submission.student),
            joinedload(Submission.variant).joinedload(TestVariant.test).joinedload(Test.author)
        )
        .where(Submission.id == submission.id)
    )
    submission = result.unique().scalar_one()
    
    # Добавляем time_limit в объект для схемы
    submission.time_limit = submission.variant.test.settings.get("time_limit")
    
    return submission


@router.get("", response_model=List[TestListResponse])
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
    query = select(Test).join(User, Test.author_id == User.id).options(
        selectinload(Test.author)
    )
    
    # Students видят только опубликованные тесты
    if current_user.role == Role.STUDENT:
        query = query.where(Test.status == TestStatus.PUBLISHED)
    # Teacher видит свои тесты + тесты администраторов
    elif current_user.role == Role.TEACHER:
        query = query.where(
            (Test.author_id == current_user.id) | (User.role == Role.ADMIN)
        )
    
    if status:
        if isinstance(status, str):
            status = TestStatus(status)
        query = query.where(Test.status == status)
    
    query = query.offset(skip).limit(limit).order_by(Test.created_at.desc())
    result = await db.execute(query)
    tests = result.scalars().all()
    
    return tests


async def check_test_structure_availability(
    db: AsyncSession, 
    structure: List[dict], 
    exclude_ids: List[UUID] = None
):
    """
    Проверка наличия достаточного количества вопросов для формирования структуры теста
    """
    from app.models.question import Question
    from app.models.topic import Topic
    
    errors = []
    requirements = {}
    for rule in structure:
        key = (rule.get("topic_id"), rule.get("question_type"), rule.get("difficulty", 1))
        requirements[key] = requirements.get(key, 0) + rule.get("count", 0)
        
    for (topic_id, q_type, difficulty), count_needed in requirements.items():
        query = select(func.count(Question.id)).where(
            Question.topic_id == topic_id,
            Question.type == q_type,
            Question.difficulty == difficulty
        )
        if exclude_ids:
            query = query.where(~Question.id.in_(exclude_ids))
            
        count_available = await db.scalar(query) or 0
        
        if count_available < count_needed:
            topic = await db.get(Topic, UUID(topic_id) if isinstance(topic_id, str) else topic_id)
            topic_name = topic.name if topic else str(topic_id)
            errors.append(
                f"Тема '{topic_name}' ({q_type}): нужно {count_needed}, доступно {count_available}"
            )
            
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недостаточно вопросов для указанной структуры: " + "; ".join(errors)
        )


@router.post("", response_model=TestResponse, status_code=status.HTTP_201_CREATED)
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
    
    test_data = test_in.model_dump(mode='json')
    structure_data = test_data.get("structure")
    
    # Валидация достаточности вопросов
    if structure_data:
        fixed_ids = [q.question_id for q in test_in.questions]
        await check_test_structure_availability(db, structure_data, exclude_ids=fixed_ids)
        
    test = Test(
        author_id=current_user.id,
        title=test_in.title,
        description=test_in.description,
        settings=test_data.get("settings", {}),
        structure=structure_data,
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
        )
        db.add(test_question)
    
    await db.commit()
    
    # Возвращаем тест со всеми загруженными связями для TestResponse
    result = await db.execute(
        select(Test)
        .options(
            selectinload(Test.author),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.topic),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.image),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.author)
        )
        .where(Test.id == test.id)
    )
    test = result.scalar_one()
    populate_test_question_urls(test)
    
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
        .options(
            selectinload(Test.author),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.topic),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.image),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.author)
        )
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
    
    # Проверка прав доступа: Teacher может видеть свои или админские тесты
    if current_user.role == Role.TEACHER:
        # Нам нужно проверить роль автора теста
        author_result = await db.execute(select(User.role).where(User.id == test.author_id))
        author_role = author_result.scalar_one_or_none()
        
        if test.author_id != current_user.id and author_role != Role.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
    
    populate_test_question_urls(test)
    
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
    result = await db.execute(
        select(Test)
        .options(
            selectinload(Test.author),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.topic),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.image),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.author)
        )
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
    
    update_data = test_update.model_dump(exclude_unset=True, mode='json')
    
    # Конвертируем структуру в dict и валидируем
    if "structure" in update_data and update_data["structure"] is not None:
        # Для валидации используем либо новые вопросы из update_data, либо текущие из базы
        fixed_ids = []
        if "questions" in update_data:
            fixed_ids = [UUID(q["question_id"]) if isinstance(q["question_id"], str) else q["question_id"] for q in update_data["questions"]]
        else:
            fixed_ids = [tq.question_id for tq in test.test_questions]
            
        await check_test_structure_availability(db, update_data["structure"], exclude_ids=fixed_ids)
        
    # Обработка обновления вопросов
    if "questions" in update_data:
        new_questions_data = update_data.pop("questions")
        
        # Очищаем старые вопросы (cascade="all, delete-orphan" удалит их из базы)
        test.test_questions = []
        
        # Добавляем новые
        for q_data in new_questions_data:
            q_id = UUID(q_data["question_id"]) if isinstance(q_data["question_id"], str) else q_data["question_id"]
            
            # Проверка существования вопроса (необязательно, если доверяем фронтенду, но лучше оставить)
            result = await db.execute(select(Question).where(Question.id == q_id))
            if not result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Question {q_id} not found"
                )
            
            test_question = TestQuestion(
                test_id=test.id,
                question_id=q_id,
                order=q_data["order"],
            )
            test.test_questions.append(test_question)

    for field, value in update_data.items():
        setattr(test, field, value)
    
    await db.commit()
    
    # Возвращаем тест со всеми загруженными связями для TestResponse
    result = await db.execute(
        select(Test)
        .options(
            selectinload(Test.author),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.topic),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.image),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.author)
        )
        .where(Test.id == test.id)
    )
    test = result.scalar_one()
    populate_test_question_urls(test)
    
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
        .options(
            selectinload(Test.author),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.topic),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.image),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.author)
        )
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
    
    # Проверка наличия вопросов (фиксированных или структуры для генерации)
    if not test.test_questions and not test.structure:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot publish test without questions or structure"
        )
    
    # Публикация
    from datetime import datetime
    test.status = TestStatus.PUBLISHED
    test.published_at = datetime.utcnow()
    
    # Генерация варианта
    fixed_question_ids = [tq.question_id for tq in test.test_questions]
    
    if test.structure:
        # Если есть структура, генерируем дополнительные вопросы
        generated_ids = await generate_test_variant_questions(
            db, test.structure, exclude_ids=fixed_question_ids
        )
        question_ids = fixed_question_ids + generated_ids
    else:
        # Если нет структуры, используем только привязанные вопросы
        question_ids = fixed_question_ids
    
    # Convert UUIDs to strings for JSONB serialization
    question_ids_str = [str(qid) for qid in question_ids]
    
    variant = TestVariant(
        test_id=test.id,
        variant_code=secrets.token_urlsafe(8),
        question_order=question_ids_str,
    )
    
    db.add(variant)
    await db.commit()
    
    # Возвращаем тест со всеми загруженными связями для TestResponse
    result = await db.execute(
        select(Test)
        .options(
            selectinload(Test.author),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.topic),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.image),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.author)
        )
        .where(Test.id == test.id)
    )
    test = result.scalar_one()
    populate_test_question_urls(test)
    
    return test


@router.post("/{test_id}/unpublish", response_model=TestResponse)
async def unpublish_test(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Снятие теста с публикации
    """
    result = await db.execute(
        select(Test)
        .options(
            selectinload(Test.author),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.topic),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.image),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.author)
        )
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
    
    if test.status != TestStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test is not published"
        )
    
    test.status = TestStatus.DRAFT
    test.published_at = None
    await db.commit()
    
    # Релоад для ответа
    result = await db.execute(
        select(Test)
        .options(
            selectinload(Test.author),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.topic),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.image),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.author)
        )
        .where(Test.id == test.id)
    )
    test = result.scalar_one()
    populate_test_question_urls(test)
    
    return test


@router.post("/{test_id}/duplicate", response_model=TestResponse)
async def duplicate_test(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Создание дубликата теста (текущий пользователь становится автором)
    """
    if current_user.role not in [Role.TEACHER, Role.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    # 1. Получаем исходный тест со всеми связями
    result = await db.execute(
        select(Test)
        .options(
            selectinload(Test.author),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.topic),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.image),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.author)
        )
        .where(Test.id == test_id)
    )
    original_test = result.scalar_one_or_none()

    if not original_test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )

    # 2. Проверка прав: Teacher может дублировать свои или админские тесты
    if current_user.role == Role.TEACHER:
        if original_test.author_id != current_user.id and original_test.author.role != Role.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to duplicate this test"
            )

    # 3. Создаем новый тест
    new_test = Test(
        author_id=current_user.id,
        title=f"{original_test.title} (копия)",
        description=original_test.description,
        settings=original_test.settings.copy() if original_test.settings else {},
        structure=original_test.structure.copy() if original_test.structure else None,
        status=TestStatus.DRAFT,
    )
    
    db.add(new_test)
    await db.flush() # Получаем ID нового теста

    # 4. Копируем вопросы
    for tq in original_test.test_questions:
        new_tq = TestQuestion(
            test_id=new_test.id,
            question_id=tq.question_id,
            order=tq.order,
        )
        db.add(new_tq)

    await db.commit()

    # 5. Возвращаем новый тест со всеми связями
    result = await db.execute(
        select(Test)
        .options(
            selectinload(Test.author),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.topic),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.image),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.author)
        )
        .where(Test.id == new_test.id)
    )
    new_test = result.scalar_one()
    populate_test_question_urls(new_test)

    return new_test


async def generate_test_variant_questions(
    db: AsyncSession, 
    structure: List[dict], 
    exclude_ids: List[UUID] = None
) -> List[UUID]:
    """
    Генерация списка ID вопросов на основе структуры теста.
    Используется только точное совпадение по теме и типу.
    """
    import random
    from app.models.question import Question
    
    selected_ids = []
    base_exclude = list(exclude_ids) if exclude_ids else []
    
    for rule in structure:
        topic_id = rule.get("topic_id")
        q_type = rule.get("question_type")
        difficulty = rule.get("difficulty", 1)
        count_needed = rule.get("count", 0)
        
        # Только точное совпадение (Тема + Тип + Сложность)
        # Исключаем уже выбранные в этом проходе и переданные извне (фиксированные)
        current_exclude = base_exclude + selected_ids
        
        query = select(Question.id).where(
            Question.topic_id == topic_id,
            Question.type == q_type,
            Question.difficulty == difficulty
        )
        if current_exclude:
            query = query.where(~Question.id.in_(current_exclude))
            
        result = await db.execute(query)
        available_ids = [r[0] for r in result.all()]
        
        if len(available_ids) < count_needed:
            # Если после валидации при сохранении вопросы были удалены,
            # берем максимум возможного из того что осталось
            selected_ids.extend(available_ids)
        else:
            picked = random.sample(available_ids, count_needed)  # nosec B311
            selected_ids.extend(picked)
                
    return selected_ids


@router.get("/{test_id}/variants", response_model=List[TestVariantResponse])
async def get_test_variants(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение всех вариантов теста
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


@router.get("/variants/{variant_id}", response_model=TestVariantResponse)
async def get_variant(
    variant_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение конкретного варианта по ID
    """
    result = await db.execute(select(TestVariant).where(TestVariant.id == variant_id))
    variant = result.scalar_one_or_none()
    
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant not found"
        )
    
    return variant


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

    # Проверка наличия результатов
    from sqlalchemy import exists
    sub_query = select(exists().where(Submission.variant_id.in_(
        select(TestVariant.id).where(TestVariant.test_id == test_id)
    )))
    has_submissions = await db.scalar(sub_query)
    
    if has_submissions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить тест, у которого есть результаты прохождения. Сначала удалите результаты или архивируйте тест."
        )

    try:
        await db.delete(test)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e
    
    return None

