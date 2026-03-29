
import asyncio
import json
import numpy as np
from uuid import uuid4
from app.services.cv_service import cv_service

def print_breakdown(res):
    print(f"--- Результат: Score={res['total_score']} (IoU={res['iou']}, Recall={res['recall']}, Precision={res['precision']}) ---")
    print(f"| {'ID Метки':<10} | {'Режим':<10} | {'Найдено':<10} | {'Recall':<8} | {'Accuracy':<10} |")
    print("-" * 65)
    for lb in res['labels_breakdown']:
        print(f"| {lb['label_id']:<10} | {lb['mode']:<10} | {lb['found_count']}/{lb['total_count']:<8} | {lb['recall']:<8} | {lb['avg_accuracy']:<10} |")
    print("-" * 65)
    print(f"Всего TP: {res['total_true_positives']}, Студент нарисовал: {res['total_valid_stud_count']}")
    print("\n")

async def run_test_case(name, stud_ann, ref_ann, config):
    print(f"=== ТЕСТ: {name} ===")
    res = await cv_service.evaluate_annotation(
        student_data={"annotations": stud_ann},
        reference_data={"annotations": ref_ann},
        config=config
    )
    print_breakdown(res)
    return res

async def test_flexible_scoring():
    # 1. Обратная совместимость (без label_configs)
    # Студент нашел 1 из 2. Ожидаем Recall 0.5
    ref_1 = [
        {"label_id": "L1", "points": [0,0, 10,0, 10,10, 0,10]},
        {"label_id": "L1", "points": [20,20, 30,20, 30,30, 20,30]}
    ]
    stud_1 = [
        {"label_id": "L1", "points": [0,0, 10,0, 10,10, 0,10]}
    ]
    await run_test_case("Обратная совместимость (нет конфига)", stud_1, ref_1, {})

    # 2. Режим 'all' для конкретной метки
    # Студент нашел 1 из 2. Ожидаем Recall 0.5 для этой метки
    config_2 = {
        "label_configs": {
            "L1": {"mode": "all", "weight": 1.0}
        }
    }
    await run_test_case("Режим 'all' (найдено 1/2)", stud_1, ref_1, config_2)

    # 3. Режим 'at_least_n' (N=1)
    # Студент нашел 1 из 2. Т.к. N=1, Recall должен быть 1.0 (100%)
    config_3 = {
        "label_configs": {
            "L1": {"mode": "at_least_n", "min_count": 1, "weight": 1.0}
        }
    }
    await run_test_case("Режим 'at_least_n' (N=1, найдено 1/2)", stud_1, ref_1, config_3)

    # 4. Глобальная точность (лишние аннотации)
    # Студент нарисовал 3 контура: 1 верный L1, 1 лишний L1, 1 контур метки L2 (которой нет в конфиге)
    # Ожидаем сильное снижение Precision
    ref_4 = [
        {"label_id": "L1", "points": [0,0, 10,0, 10,10, 0,10]}
    ]
    stud_4 = [
        {"label_id": "L1", "points": [0,0, 10,0, 10,10, 0,10]}, # Ок
        {"label_id": "L1", "points": [50,50, 60,50, 60,60, 50,60]}, # Лишний
        {"label_id": "L2", "points": [100,100, 110,100, 110,110, 100,110]} # Лишний (не в конфиге)
    ]
    config_4 = {
        "label_configs": {
            "L1": {"mode": "all", "weight": 1.0}
        }
    }
    await run_test_case("Глобальная точность (2 лишних контура)", stud_4, ref_4, config_4)

    # 5. Веса меток
    # L1 (Tumor) вес 5, L2 (Vessel) вес 1.
    # Студент нашел только Tumor. Recall должен быть очень высоким.
    ref_5 = [
        {"label_id": "Tumor", "points": [0,0, 10,0, 10,10, 0,10]},
        {"label_id": "Vessel", "points": [20,20, 30,20, 30,30, 20,30]}
    ]
    stud_5 = [
        {"label_id": "Tumor", "points": [0,0, 10,0, 10,10, 0,10]}
    ]
    config_5 = {
        "label_configs": {
            "Tumor": {"mode": "all", "weight": 5.0},
            "Vessel": {"mode": "all", "weight": 1.0}
        }
    }
    await run_test_case("Взвешенные метки (Важный Tumor найден, Vessel - нет)", stud_5, ref_5, config_5)

    # 6. Частичный зачет (Inclusion) только для одной метки
    # Студент нарисовал маленький квадрат внутри большого эталона.
    # Для L1 включен Inclusion, для L2 - нет (IoU).
    ref_6 = [
        {"label_id": "L1", "points": [0,0, 100,0, 100,100, 0,100]}, # Большой
        {"label_id": "L2", "points": [200,200, 300,200, 300,300, 200,300]} # Большой
    ]
    stud_6 = [
        {"label_id": "L1", "points": [10,10, 20,10, 20,20, 10,20]}, # Маленький внутри
        {"label_id": "L2", "points": [210,210, 220,210, 220,220, 210,220]}  # Маленький внутри
    ]
    config_6 = {
        "allow_partial": False, # Глобально выкл
        "label_configs": {
            "L1": {"mode": "all", "allow_partial": True, "weight": 1.0}, # Для L1 ВКЛ
            "L2": {"mode": "all", "allow_partial": False, "weight": 1.0}  # Для L2 ВЫКЛ
        },
        "inclusion_threshold": 0.8,
        "min_coverage_threshold": 0.01 # Покрытие 1%
    }
    await run_test_case("Индивидуальный частичный зачет (L1 - да, L2 - нет)", stud_6, ref_6, config_6)

    # 7. Самопересекающаяся геометрия (Звезда)
    # Звезда с самопересечением в центре
    star_points = [50,0, 60,40, 100,50, 60,60, 50,100, 40,60, 0,50, 40,40, 50,0]
    ref_7 = [{"label_id": "Star", "points": star_points}]
    stud_7 = [{"label_id": "Star", "points": star_points}]
    config_7 = {"label_configs": {"Star": {"mode": "all"}}}
    await run_test_case("Сложная геометрия (Звезда)", stud_7, ref_7, config_7)

if __name__ == "__main__":
    asyncio.run(test_flexible_scoring())
