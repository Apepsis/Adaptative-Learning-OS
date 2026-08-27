from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "adaptive_learning_os",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks.ingestion"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=True,
    worker_hijack_root_logger=False,
)
