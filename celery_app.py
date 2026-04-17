from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
    "tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=["app.tasks.cleanup","app.tasks.db_flush"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    "cleanup-expired-urls-every-hour": {
        "task": "app.tasks.cleanup.cleanup_expired_urls",
        "schedule": crontab(minute="0", hour="*"),  # every hour
    },
    "flush-db-every-30-minutes": {
        "task": "app.tasks.db_flush.flush_db",
        "schedule": crontab(minute="*/30"),  # every 30 minutes
    },
}
