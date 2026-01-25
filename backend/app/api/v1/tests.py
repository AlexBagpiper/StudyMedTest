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
    result = await db.execute(
        select(Submission)
        .join(TestVariant)
        .where(
            Submission.student_id == current_user.id,
            Submission.status == SubmissionStatus.IN_PROGRESS,
            TestVariant.test_id == test_id
        )
    )
    existing_submission = result.scalar_one_or_none()
    if existing_submission:
        # Если есть уже начатая попытка, возвращаем её вместо создания новой
        result = await db.execute(
            select(Submission)
            .options(
                selectinload(Submission.answers),
                selectinload(Submission.variant)
            )
            .where(Submission.id == existing_submission.id)
        )
        return result.scalar_one()

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
        
    variant = TestVariant(
        test_id=test.id,
        variant_code=secrets.token_urlsafe(8),
        question_order=question_ids,
    )
    db.add(variant)
    await db.flush() # Получаем ID варианта
    
    # 4. Создание submission
    submission = Submission(
        student_id=current_user.id,
        variant_id=variant.id,
        status=SubmissionStatus.IN_PROGRESS,
    )
    db.add(submission)
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
    # #region agent log
    import json
    import traceback
    log_path = r"e:\pythonProject\StudyMedTest\.cursor\debug.log"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"tests.py:144","message":"list_tests entry","data":{"skip":skip,"limit":limit,"status":str(status) if status else None,"user_id":str(current_user.id) if current_user else None,"user_role":str(current_user.role) if current_user else None},"timestamp":int(__import__("time").time()*1000)})+"\n")
    except: pass
    # #endregion
    
    query = select(Test)
    
    # Students видят только опубликованные тесты
    if current_user.role == Role.STUDENT:
        query = query.where(Test.status == TestStatus.PUBLISHED)
    # Teacher видит только свои тесты
    elif current_user.role == Role.TEACHER:
        query = query.where(Test.author_id == current_user.id)
    
    if status:
        if isinstance(status, str):
            status = TestStatus(status)
        query = query.where(Test.status == status)
    
    # #region agent log
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"tests.py:169","message":"before SQL execute","data":{"query_str":str(query)},"timestamp":int(__import__("time").time()*1000)})+"\n")
    except: pass
    # #endregion
    
    query = query.offset(skip).limit(limit).order_by(Test.created_at.desc())
    
    # #region agent log
    try:
        result = await db.execute(query)
        tests = result.scalars().all()
        print(f"[DEBUG] list_tests: SQL executed successfully, found {len(tests)} tests")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"tests.py:171","message":"after SQL execute","data":{"tests_count":len(tests)},"timestamp":int(__import__("time").time()*1000)})+"\n")
    except Exception as e:
        error_tb = traceback.format_exc()
        print(f"[ERROR] list_tests: SQL execute failed: {type(e).__name__}: {str(e)}")
        print(f"[ERROR] Traceback:\n{error_tb}")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"tests.py:171","message":"SQL execute error","data":{"error":str(e),"traceback":error_tb},"timestamp":int(__import__("time").time()*1000)})+"\n")
        raise
    # #endregion
    
    # #region agent log
    for i, test in enumerate(tests):
        try:
            test_data = {"id":str(test.id),"author_id":str(test.author_id),"status":str(test.status) if test.status else None,"title":test.title[:50] if test.title else None,"settings_type":type(test.settings).__name__ if test.settings else None,"structure_type":type(test.structure).__name__ if test.structure else None,"created_at":str(test.created_at) if test.created_at else None,"updated_at":str(test.updated_at) if test.updated_at else None,"published_at":str(test.published_at) if test.published_at else None}
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"tests.py:173","message":"test data before serialization","data":{"test_index":i,**test_data},"timestamp":int(__import__("time").time()*1000)})+"\n")
            if i == 0:  # Логируем только первый тест в stdout
                print(f"[DEBUG] list_tests: First test data: id={test.id}, status={test.status}, title={test.title[:30] if test.title else None}")
        except Exception as e:
            print(f"[ERROR] list_tests: Error reading test {i} data: {str(e)}")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"tests.py:173","message":"error reading test data","data":{"test_index":i,"error":str(e)},"timestamp":int(__import__("time").time()*1000)})+"\n")
    # #endregion
    
    # #region agent log
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"tests.py:173","message":"before return serialization","data":{"tests_count":len(tests)},"timestamp":int(__import__("time").time()*1000)})+"\n")
    except: pass
    # #endregion
    
    try:
        print(f"[DEBUG] list_tests: Attempting to serialize {len(tests)} tests")
        return tests
    except Exception as e:
        # #region agent log
        error_traceback = traceback.format_exc()
        error_info = {"error":str(e),"error_type":type(e).__name__,"traceback":error_traceback}
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"tests.py:173","message":"serialization error","data":error_info,"timestamp":int(__import__("time").time()*1000)})+"\n")
        except: pass
        print(f"[ERROR] list_tests serialization error: {type(e).__name__}: {str(e)}")
        print(f"[ERROR] Traceback:\n{error_traceback}")
        # #endregion
        raise


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
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.topic),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.image)
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
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.topic),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.image)
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
    
    if current_user.role == Role.TEACHER and test.author_id != current_user.id:
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
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.topic),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.image)
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
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.topic),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.image)
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
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.topic),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.image)
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
    
    variant = TestVariant(
        test_id=test.id,
        variant_code=secrets.token_urlsafe(8),
        question_order=question_ids,
    )
    
    db.add(variant)
    await db.commit()
    
    # Возвращаем тест со всеми загруженными связями для TestResponse
    result = await db.execute(
        select(Test)
        .options(
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.topic),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.image)
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
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.topic),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.image)
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
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.topic),
            selectinload(Test.test_questions).selectinload(TestQuestion.question).selectinload(Question.image)
        )
        .where(Test.id == test.id)
    )
    test = result.scalar_one()
    populate_test_question_urls(test)
    
    return test


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
            picked = random.sample(available_ids, count_needed)
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

