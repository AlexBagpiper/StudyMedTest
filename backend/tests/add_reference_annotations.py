"""
Скрипт для добавления эталонных аннотаций к графическому вопросу
"""
import asyncio
import sys
import os
from uuid import UUID

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.question import Question, QuestionType


async def add_sample_annotations(question_id: str = None):
    """Добавить пример эталонных аннотаций к графическому вопросу
    
    Args:
        question_id: ID конкретного вопроса (опционально). 
                     Если не указан, обновляются ВСЕ графические вопросы
    """
    async with AsyncSessionLocal() as session:
        if question_id:
            # Находим конкретный вопрос
            result = await session.execute(
                select(Question).where(Question.id == UUID(question_id))
            )
            questions = [result.scalar_one_or_none()]
            if not questions[0]:
                print(f"❌ Вопрос с ID {question_id} не найден")
                return
        else:
            # Находим ВСЕ графические вопросы
            result = await session.execute(
                select(Question)
                .where(Question.type == QuestionType.IMAGE_ANNOTATION)
            )
            questions = list(result.scalars().all())
            
            if not questions:
                print("❌ Не найдено вопросов с типом IMAGE_ANNOTATION")
                return
        
        print(f"✅ Найдено вопросов: {len(questions)}")
        
        for question in questions:
            print(f"\n📝 Вопрос ID: {question.id}")
            print(f"   Текущий reference_data: {question.reference_data}")
        
            # Создаём примеры эталонных аннотаций
            # Вариант 1: Прямоугольник
            sample_annotations = [
                {
                    "id": "ref_ann_1",
                    "label_id": "tumor",  # ID метки из labels
                    "type": "rectangle",
                    "bbox": [100, 100, 150, 120]  # x, y, width, height
                },
                {
                    "id": "ref_ann_2",
                    "label_id": "tumor",
                    "type": "rectangle",
                    "bbox": [300, 200, 80, 90]
                }
            ]
            
            # Обновляем reference_data
            question.reference_data = {
                "annotations": sample_annotations,
                "labels": [
                    {
                        "id": "tumor",
                        "name": "Опухоль",
                        "color": "#FF0000"
                    }
                ]
            }
            
            print(f"   ✅ Добавлено аннотаций: {len(sample_annotations)}")
        
        await session.commit()
        
        print(f"\n✅ Все вопросы обновлены!")
        print(f"📝 Теперь можно запустить test_cv_annotation_real.py")


if __name__ == "__main__":
    import sys
    
    # Можно передать ID вопроса как аргумент:
    # python add_reference_annotations.py a9d359b3-0a65-4cad-a982-8800acd243a5
    question_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    if question_id:
        print(f"Обновление вопроса с ID: {question_id}")
    else:
        print("Обновление ВСЕХ графических вопросов")
    
    asyncio.run(add_sample_annotations(question_id))
