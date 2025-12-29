"""
Celery application configuration
"""

from celery import Celery

from app.core.config import settings

# Создание Celery app
celery_app = Celery(
    "medtest",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.evaluation_tasks",
    ]
)

# Конфигурация
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    worker_prefetch_multiplier=1,  # Для длительных задач
    worker_max_tasks_per_child=50,  # Перезапуск worker после 50 задач
)

# Routes для разных типов задач
celery_app.conf.task_routes = {
    "app.tasks.evaluation_tasks.evaluate_text_answer": {"queue": "llm"},
    "app.tasks.evaluation_tasks.evaluate_annotation_answer": {"queue": "cv"},
    "app.tasks.evaluation_tasks.evaluate_submission": {"queue": "default"},
}

if __name__ == "__main__":
    celery_app.start()

