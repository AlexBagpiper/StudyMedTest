import asyncio
import json
import logging
from uuid import uuid4
from datetime import datetime

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User, Role
from app.models.system_config import SystemConfig
from app.core.security import get_password_hash
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def initialize_admin(db):
    """Создание первичного администратора"""
    result = await db.execute(
        select(User).where(User.email == settings.FIRST_ADMIN_EMAIL)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        logger.info(f"Admin {settings.FIRST_ADMIN_EMAIL} already exists.")
        return
    
    admin = User(
        email=settings.FIRST_ADMIN_EMAIL,
        password_hash=get_password_hash(settings.FIRST_ADMIN_PASSWORD),
        last_name='Администратор',
        first_name='Системы',
        role=Role.ADMIN,
        is_active=True,
        is_verified=True
    )
    db.add(admin)
    logger.info(f"Admin {settings.FIRST_ADMIN_EMAIL} created successfully.")

async def initialize_configs(db):
    """Инициализация системных настроек по умолчанию"""
    configs = {
        "cv_evaluation_params": {
            "value": {
                "iou_weight": 0.5,
                "recall_weight": 0.3,
                "precision_weight": 0.2,
                "iou_threshold": 0.5,
                "inclusion_threshold": 0.8,
                "min_coverage_threshold": 0.05,
                "loyalty_mode": True,
                "accuracy_grace_threshold": 0.95,
                "loyalty_boost_enabled": True,
                "loyalty_boost_value": 0.05,
                "top_off_threshold": 99.0,
                "label_configs": {}
            },
            "description": "Параметры оценки графических заданий (CV) и механизмы лояльности"
        },
        "llm_evaluation_params": {
            "value": {
                "yandex_model": "yandexgpt-lite/latest",
                "strategy": "yandex",
                "ai_threshold_warning": 0.5,
                "ai_threshold_error": 0.8,
                "plagiarism_threshold": 0.5,
                "ai_check_enabled": True,
                "plagiarism_check_enabled": True
            },
            "description": "Параметры оценки текстовых заданий (LLM) и настройки анти-чита"
        }
    }

    for key, data in configs.items():
        result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
        existing = result.scalar_one_or_none()
        
        if not existing:
            config = SystemConfig(
                id=uuid4(),
                key=key,
                value=data["value"],
                description=data["description"]
            )
            db.add(config)
            logger.info(f"System config '{key}' initialized.")
        else:
            # Обновляем структуру, если добавились новые поля в дефолты (не затирая пользовательские значения)
            current_value = existing.value
            updated = False
            for k, v in data["value"].items():
                if k not in current_value:
                    current_value[k] = v
                    updated = True
            
            if updated:
                existing.value = current_value
                logger.info(f"System config '{key}' updated with new default fields.")

async def main():
    async with AsyncSessionLocal() as db:
        try:
            await initialize_admin(db)
            await initialize_configs(db)
            await db.commit()
            logger.info("Database initialization completed successfully.")
        except Exception as e:
            await db.rollback()
            logger.error(f"Error initializing database: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(main())
