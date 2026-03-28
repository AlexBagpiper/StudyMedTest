import asyncio
import sys
import os

# Добавляем путь к приложению
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.cv_service import cv_service

async def test_cv_loyalty_mechanisms():
    print("=== Testing CV Loyalty Mechanisms ===\n")
    
    # Эталон: Прямоугольник 100x100
    reference_data = {
        "annotations": [
            {
                "id": "ref1",
                "label_id": "tumor",
                "type": "rectangle",
                "bbox": [0, 0, 100, 100] # Area 10000
            }
        ]
    }

    # 1. ТЕСТ: GRACE ZONE (Порог идеальной точности)
    # Студент нарисовал чуть больше: 100x104 (IoU = 10000 / 10400 = 0.961)
    # При пороге 0.95 это должно стать 100% точности
    student_near_perfect = {
        "annotations": [
            {
                "id": "stud1",
                "label_id": "tumor",
                "type": "rectangle",
                "bbox": [0, 0, 100, 104]
            }
        ]
    }
    
    config_grace = {
        "loyalty_mode": True,
        "accuracy_grace_threshold": 0.95,
        "iou_weight": 1.0, # Оцениваем только точность для чистоты теста
        "recall_weight": 0.0,
        "precision_weight": 0.0
    }
    
    result_grace = await cv_service.evaluate_annotation(student_near_perfect, reference_data, config=config_grace)
    print(f"Grace Zone Test (IoU 0.961 -> 1.0):")
    print(f"  Result Score: {result_grace['total_score']}")
    assert result_grace['total_score'] == 100.0
    
    # 2. ТЕСТ: LOYALTY BOOST (Бонус за клиническую безошибочность)
    # Студент попал на 90% (IoU = 0.9), но нашел всё и не добавил лишнего.
    # Должен получить +5% к точности -> 95%
    student_boost = {
        "annotations": [
            {
                "id": "stud1",
                "label_id": "tumor",
                "type": "rectangle",
                "bbox": [0, 0, 100, 111.11] # IoU ~0.9
            }
        ]
    }
    
    config_boost = {
        "loyalty_mode": True,
        "accuracy_grace_threshold": 0.98, # Выключаем Grace Zone
        "loyalty_boost_enabled": True,
        "loyalty_boost_value": 0.05,
        "iou_weight": 1.0,
        "recall_weight": 0.0,
        "precision_weight": 0.0
    }
    
    result_boost = await cv_service.evaluate_annotation(student_boost, reference_data, config=config_boost)
    print(f"\nLoyalty Boost Test (IoU 0.9 + 0.05 bonus):")
    print(f"  IoU Metric: {result_boost['iou']}")
    print(f"  Result Score: {result_boost['total_score']}")
    # 0.9 + 0.05 = 0.95 * 100 = 95
    assert 94.0 < result_boost['total_score'] < 96.0

    # 2.1 ТЕСТ: CUSTOM LOYALTY BOOST VALUE
    config_custom_boost = config_boost.copy()
    config_custom_boost["loyalty_boost_value"] = 0.10 # 10% bonus
    
    result_custom_boost = await cv_service.evaluate_annotation(student_boost, reference_data, config=config_custom_boost)
    print(f"\nCustom Loyalty Boost Test (IoU 0.9 + 0.10 bonus):")
    print(f"  IoU Metric: {result_custom_boost['iou']}")
    print(f"  Result Score: {result_custom_boost['total_score']}")
    # 0.9 + 0.10 = 1.0 * 100 = 100
    assert result_custom_boost['total_score'] == 100.0

    # 3. ТЕСТ: TOP-OFF RULE (Округление итога)
    # Студент набрал 99.2% итога. Должно стать 100%.
    config_topoff = {
        "loyalty_mode": True,
        "top_off_threshold": 99.0,
        "iou_weight": 0.5,
        "recall_weight": 0.3,
        "precision_weight": 0.2,
        "accuracy_grace_threshold": 1.0, # Выкл
        "loyalty_boost_enabled": False   # Выкл
    }
    
    # Делаем IoU таким, чтобы итог был ~99.2
    # Recall=1 (0.3), Precision=1 (0.2). Нужно 0.492 от IoU (0.492 / 0.5 = 0.984 IoU)
    student_topoff = {
        "annotations": [
            {
                "id": "stud1",
                "label_id": "tumor",
                "type": "rectangle",
                "bbox": [0, 0, 100, 101.6] # IoU ~ 0.984
            }
        ]
    }
    
    result_topoff = await cv_service.evaluate_annotation(student_topoff, reference_data, config=config_topoff)
    print(f"\nTop-off Rule Test (Score 99.2 -> 100):")
    print(f"  Original Score logic check (IoU={result_topoff['iou']}):")
    print(f"  Final Score: {result_topoff['total_score']}")
    assert result_topoff['total_score'] == 100.0

    # 4. ТЕСТ: ВЫКЛЮЧЕННАЯ ЛОЯЛЬНОСТЬ
    # Тот же сценарий что и Grace Zone, но loyalty_mode = False
    result_disabled = await cv_service.evaluate_annotation(student_near_perfect, reference_data, config={"loyalty_mode": False})
    print(f"\nDisabled Loyalty Test:")
    print(f"  Result Score: {result_disabled['total_score']}")
    assert result_disabled['total_score'] < 100.0

    # 5. СЛОЖНЫЙ СЦЕНАРИЙ: Несколько объектов
    reference_multi = {
        "annotations": [
            {"type": "rectangle", "bbox": [0, 0, 10, 10]}, # Объект 1
            {"type": "rectangle", "bbox": [50, 50, 10, 10]} # Объект 2
        ]
    }
    
    # Студент нашел оба, один идеально, один на 90%
    student_multi = {
        "annotations": [
            {"type": "rectangle", "bbox": [0, 0, 10, 10]},
            {"type": "rectangle", "bbox": [50, 50, 10, 11.1]} # IoU ~ 0.9
        ]
    }
    # Средний IoU = (1.0 + 0.9) / 2 = 0.95
    # С лояльностью Grace Zone (0.95) это должно стать 100%
    
    result_multi = await cv_service.evaluate_annotation(student_multi, reference_multi, config=config_grace)
    print(f"\nMulti-object Loyalty Test (Avg IoU 0.95 -> 1.0):")
    print(f"  Result Score: {result_multi['total_score']}")
    assert result_multi['total_score'] == 100.0

    print("\n=== All CV Loyalty tests passed! ===")

if __name__ == "__main__":
    asyncio.run(test_cv_loyalty_mechanisms())
