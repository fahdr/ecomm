"""
Celery application configuration.

Sets up the Celery app with Redis broker and result backend.
Each service has its own Celery instance with an independent queue.

For Developers:
    Import `celery_app` when defining tasks. Tasks are auto-discovered
    from app.tasks modules. Use `@celery_app.task` decorator.

For QA Engineers:
    Run worker: `celery -A app.tasks.celery_app worker --loglevel=info`
    Run beat: `celery -A app.tasks.celery_app beat --loglevel=info`

For Project Managers:
    Celery handles background jobs like scheduled research runs,
    content generation, email sending, etc.
"""

from celery import Celery

from app.config import settings

celery_app = Celery(
    settings.service_name,
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue=settings.service_name,
    beat_schedule={
        # Add scheduled tasks here per service
        # "example-task": {
        #     "task": "app.tasks.example.run_example",
        #     "schedule": crontab(hour=0, minute=0),
        # },
    },
)

# Auto-discover tasks in app.tasks package
celery_app.autodiscover_tasks(["app.tasks"])
