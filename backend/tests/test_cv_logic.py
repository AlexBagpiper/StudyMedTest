import asyncio
import sys
import os

# Добавляем путь к приложению
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.cv_service import cv_service

async def test_cv_evaluation():
    print("Starting CV Evaluation Test...")
    
    # 1. Эталонная аннотация (прямоугольник 10x10 в точке 10,10)
    reference_data = {
        "annotations": [
            {
                "id": "ref1",
                "label_id": "label_tumor",
                "type": "rectangle",
                "bbox": [10, 10, 10, 10] # x, y, w, h
            }
        ]
    }
    
    # 2. Ответ студента - идеальное совпадение
    student_perfect = {
        "annotations": [
            {
                "id": "stud1",
                "label_id": "label_tumor",
                "type": "rectangle",
                "bbox": [10, 10, 10, 10]
            }
        ]
    }
    
    result_perfect = await cv_service.evaluate_annotation(student_perfect, reference_data)
    print(f"\nPerfect Match Result:")
    print(f"IoU: {result_perfect['iou']}")
    print(f"Recall: {result_perfect['recall']}")
    print(f"Precision: {result_perfect['precision']}")
    print(f"Total Score: {result_perfect['total_score']}")
    
    assert result_perfect['total_score'] == 100.0
    
    # 3. Ответ студента - частичное совпадение (смещение на 5 пикселей)
    # Пересечение: [15, 10, 5, 10] -> Area = 50
    # Объединение: [10, 10, 15, 10] -> Area = 150
    # IoU = 50 / 150 = 0.333
    student_partial = {
        "annotations": [
            {
                "id": "stud2",
                "label_id": "label_tumor",
                "type": "rectangle",
                "bbox": [15, 10, 10, 10]
            }
        ]
    }
    
    result_partial = await cv_service.evaluate_annotation(student_partial, reference_data)
    print(f"\nPartial Match Result (IoU ~0.33):")
    print(f"IoU: {result_partial['iou']}")
    print(f"Recall: {result_partial['recall']}")
    print(f"Precision: {result_partial['precision']}")
    print(f"Total Score: {result_partial['total_score']}")
    
    # 4. Ответ студента - лишняя аннотация (влияет на Precision)
    student_extra = {
        "annotations": [
            {
                "id": "stud1",
                "label_id": "label_tumor",
                "type": "rectangle",
                "bbox": [10, 10, 10, 10]
            },
            {
                "id": "stud_extra",
                "label_id": "label_tumor",
                "type": "rectangle",
                "bbox": [50, 50, 10, 10]
            }
        ]
    }
    
    result_extra = await cv_service.evaluate_annotation(student_extra, reference_data)
    print(f"\nExtra Annotation Result (Precision 0.5):")
    print(f"IoU: {result_extra['iou']}")
    print(f"Recall: {result_extra['recall']}")
    print(f"Precision: {result_extra['precision']}")
    print(f"Total Score: {result_extra['total_score']}")

    # 5. Ответ студента - дубликаты (должны дедуплицироваться)
    student_duplicates = {
        "annotations": [
            {
                "id": "stud1",
                "label_id": "label_tumor",
                "type": "rectangle",
                "bbox": [10, 10, 10, 10]
            },
            {
                "id": "stud1_dup",
                "label_id": "label_tumor",
                "type": "rectangle",
                "bbox": [10.01, 10.01, 10, 10] # Почти идентичен
            }
        ]
    }
    
    result_dup = await cv_service.evaluate_annotation(student_duplicates, reference_data)
    print(f"\nDuplicate Annotation Result (Should be 100 due to dedup):")
    print(f"IoU: {result_dup['iou']}")
    print(f"Recall: {result_dup['recall']}")
    print(f"Precision: {result_dup['precision']}")
    print(f"Total Score: {result_dup['total_score']}")
    
    assert result_dup['total_score'] == 100.0

if __name__ == "__main__":
    asyncio.run(test_cv_evaluation())
