import asyncio
import sys
import os
import numpy as np

# Добавляем путь к приложению
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.cv_service import cv_service

async def run_test_case(name, student_data, reference_data, config=None):
    print(f"--- Running Test: {name} ---")
    result = await cv_service.evaluate_annotation(student_data, reference_data, config=config)
    print(f"  IoU: {result['iou']}, Recall: {result['recall']}, Precision: {result['precision']}")
    print(f"  Total Score: {result['total_score']}")
    return result

async def test_cv_comprehensive():
    print("=== STARTING COMPREHENSIVE CV EVALUATION TESTS ===\n")

    # 1. ТЕСТ: Разнообразие геометрических примитивов (Polygon, Ellipse, Rectangle)
    ref_shapes = {
        "annotations": [
            {"type": "rectangle", "bbox": [10, 10, 20, 20]}, # Area 400
            {"type": "ellipse", "center": [100, 100], "radius": [10, 10]}, # Circle Area ~314
            {"points": [200, 200, 220, 200, 210, 220], "type": "polygon"} # Triangle Area 200
        ]
    }
    stud_shapes = {
        "annotations": [
            {"type": "rectangle", "bbox": [10, 10, 20, 20]}, # Perfect
            {"type": "ellipse", "center": [100, 100], "radius": [10, 10]}, # Perfect
            {"points": [200, 200, 220, 200, 210, 220], "type": "polygon"} # Perfect
        ]
    }
    await run_test_case("Shape Diversity (Perfect Match)", stud_shapes, ref_shapes)

    # 2. ТЕСТ: Пустой ответ студента
    await run_test_case("Empty Student Answer", {"annotations": []}, ref_shapes)

    # 3. ТЕСТ: Полный промах (Zero Overlap)
    stud_miss = {
        "annotations": [
            {"type": "rectangle", "bbox": [1000, 1000, 10, 10]}
        ]
    }
    await run_test_case("Complete Miss (Zero Overlap)", stud_miss, ref_shapes)

    # 4. ТЕСТ: "Шумный" студент (Много лишних аннотаций)
    stud_noisy = {
        "annotations": [
            {"type": "rectangle", "bbox": [10, 10, 20, 20]}, # Match
            {"type": "rectangle", "bbox": [500, 500, 10, 10]}, # Noise 1
            {"type": "rectangle", "bbox": [600, 600, 10, 10]}, # Noise 2
            {"type": "rectangle", "bbox": [700, 700, 10, 10]}  # Noise 3
        ]
    }
    # Recall должен быть 1/3 (0.333), Precision 1/4 (0.25)
    await run_test_case("Noisy Student (Low Precision)", stud_noisy, ref_shapes)

    # 5. ТЕСТ: Частичный зачет (Allow Partial)
    # Эталон - огромная область, студент выделил только центр (50%)
    ref_large = {"annotations": [{"type": "rectangle", "bbox": [0, 0, 100, 100]}]}
    stud_partial = {"annotations": [{"type": "rectangle", "bbox": [25, 25, 50, 50]}]}
    
    config_partial = {
        "allow_partial": True,
        "inclusion_threshold": 0.9, # Студент должен быть внутри
        "min_coverage_threshold": 0.2, # И покрыть хотя бы 20%
        "iou_threshold": 0.7 # Обычный порог IoU высокий, чтобы сработала логика частичного зачета
    }
    # В этом тесте: Inclusion = 1.0 (студент внутри), Coverage = 0.25 (2500/10000).
    # Должно засчитаться как Recall=1.0
    await run_test_case("Partial Match Logic", stud_partial, ref_large, config=config_partial)

    # 6. ТЕСТ: Комбинация весов (Weight Sensitivity)
    # Только Recall важен
    config_recall_only = {"recall_weight": 1.0, "iou_weight": 0.0, "precision_weight": 0.0}
    await run_test_case("Weight Sensitivity (Recall Only)", stud_noisy, ref_shapes, config=config_recall_only)

    # 7. ТЕСТ: Двойное срабатывание лояльности (Boost + Grace)
    # Студент нашел всё, но точность 96%.
    # 1. Grace округляет 96 -> 100.
    # 2. Boost добавляет +5% к точности (но макс 100).
    # Итог должен быть железно 100.
    config_loyalty_all = {
        "loyalty_mode": True,
        "accuracy_grace_threshold": 0.95,
        "loyalty_boost_enabled": True,
        "top_off_threshold": 99.0
    }
    student_near = {"annotations": [{"type": "rectangle", "bbox": [0, 0, 100, 104]}]} # IoU ~ 0.96
    ref_single = {"annotations": [{"type": "rectangle", "bbox": [0, 0, 100, 100]}]}
    await run_test_case("Combo Loyalty (Boost + Grace)", student_near, ref_single, config=config_loyalty_all)

    # 8. ТЕСТ: Граничный случай Top-off Rule
    # Допустим, итоговый балл 98.9, а порог 99.0. Округления НЕ должно быть.
    config_topoff_fail = {
        "loyalty_mode": True,
        "top_off_threshold": 99.0,
        "accuracy_grace_threshold": 1.0, # Выкл
        "loyalty_boost_enabled": False   # Выкл
    }
    # Подогнанный IoU 0.978 -> Score 98.9 (при весах 0.5/0.3/0.2)
    stud_98 = {"annotations": [{"type": "rectangle", "bbox": [0, 0, 100, 102.25]}]}
    await run_test_case("Top-off Rule (Just Below Threshold)", stud_98, ref_single, config=config_topoff_fail)

    # 9. ТЕСТ: Перекрывающиеся объекты (Overlapping Objects)
    # Студент нарисовал один большой контур там, где должно быть два маленьких.
    ref_overlap = {
        "annotations": [
            {"type": "rectangle", "bbox": [0, 0, 10, 10]},
            {"type": "rectangle", "bbox": [5, 5, 10, 10]} # Накладываются
        ]
    }
    stud_single_big = {
        "annotations": [
            {"type": "rectangle", "bbox": [0, 0, 15, 15]}
        ]
    }
    # Матчер должен выбрать один, второй будет пропущен (Recall 0.5)
    await run_test_case("Overlapping Objects Match", stud_single_big, ref_overlap)

    # 10. ТЕСТ: Дедупликация студенческих данных
    stud_dups = {
        "annotations": [
            {"type": "rectangle", "bbox": [0, 0, 10, 10]},
            {"type": "rectangle", "bbox": [0, 0, 10, 10]}, # Полный дубль
            {"type": "rectangle", "bbox": [0.1, 0.1, 9.9, 9.9]} # Почти дубль
        ]
    }
    # Должно считаться как 1 правильный объект, а не 1 правильный + 2 лишних.
    # Если дедупликация работает, Precision будет 1.0.
    await run_test_case("Student Duplicates Handling", stud_dups, {"annotations": [{"type": "rectangle", "bbox": [0, 0, 10, 10]}]})

    print("\n=== COMPREHENSIVE TESTS FINISHED ===")

if __name__ == "__main__":
    asyncio.run(test_cv_comprehensive())
