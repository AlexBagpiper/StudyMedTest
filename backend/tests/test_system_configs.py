import pytest
from uuid import uuid4
from sqlalchemy import select
from app.models.system_config import SystemConfig

@pytest.mark.asyncio
async def test_cv_config_persistence(db_session):
    """Тест сохранения и извлечения системных настроек CV"""
    config_key = "cv_evaluation_params"
    test_config = {
        "iou_weight": 0.7,
        "recall_weight": 0.2,
        "precision_weight": 0.1,
        "loyalty_mode": True,
        "accuracy_grace_threshold": 0.98
    }
    
    # 1. Сохраняем (используем MERGE или сначала удаляем, чтобы избежать UniqueViolation)
    config_obj = await db_session.execute(
        select(SystemConfig).where(SystemConfig.key == config_key)
    )
    obj = config_obj.scalar_one_or_none()
    
    if obj:
        obj.value = test_config
    else:
        obj = SystemConfig(key=config_key, value=test_config)
        db_session.add(obj)
    
    await db_session.commit()
    
    # 2. Извлекаем
    result = await db_session.execute(
        select(SystemConfig).where(SystemConfig.key == config_key)
    )
    saved_obj = result.scalar_one()
    assert saved_obj.value["iou_weight"] == 0.7
    assert saved_obj.value["loyalty_mode"] is True

@pytest.mark.asyncio
async def test_llm_config_persistence(db_session):
    """Тест сохранения и извлечения системных настроек LLM (анти-чит)"""
    config_key = "llm_evaluation_params"
    test_config = {
        "model": "gpt-4o",
        "temperature": 0.2,
        "plagiarism_threshold": 0.3
    }
    
    # Проверяем существование
    config_obj = await db_session.execute(
        select(SystemConfig).where(SystemConfig.key == config_key)
    )
    obj = config_obj.scalar_one_or_none()
    
    if obj:
        obj.value = test_config
    else:
        obj = SystemConfig(key=config_key, value=test_config)
        db_session.add(obj)
    
    await db_session.commit()
    
    result = await db_session.execute(
        select(SystemConfig).where(SystemConfig.key == config_key)
    )
    saved_obj = result.scalar_one()
    assert saved_obj.value["model"] == "gpt-4o"
    assert saved_obj.value["plagiarism_threshold"] == 0.3
