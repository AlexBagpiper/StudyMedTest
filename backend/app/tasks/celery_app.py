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
        "app.tasks.email_tasks",
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
    task_time_limit=30 * 60,  # 30 minutes max (для LLM задач)
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    worker_prefetch_multiplier=1,  # Для длительных задач
    worker_max_tasks_per_child=50,  # Перезапуск worker после 50 задач
    broker_connection_retry_on_startup=True,  # Решаем CPendingDeprecationWarning
    # Reliability: survive worker crashes for critical short tasks (email).
    task_reject_on_worker_lost=True,
)

# Routes для разных типов задач
celery_app.conf.task_routes = {
    "app.tasks.evaluation_tasks.evaluate_text_answer": {"queue": "celery"},
    "app.tasks.evaluation_tasks.evaluate_annotation_answer": {"queue": "celery"},
    "app.tasks.evaluation_tasks.evaluate_choice_answer": {"queue": "celery"},
    "app.tasks.evaluation_tasks.evaluate_submission": {"queue": "celery"},
    # Email tasks use names declared via @task(name=...) — see app/tasks/email_tasks.py
    "email.*": {"queue": "email"},
}

# Per-queue overrides for email: shorter time limits, higher concurrency.
celery_app.conf.task_annotations = {
    "email.*": {
        "time_limit": 60,
        "soft_time_limit": 30,
    },
}

if __name__ == "__main__":
    celery_app.start()

