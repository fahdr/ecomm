"""Celery application instance and configuration.

Creates the shared Celery app used by workers and Beat. Tasks defined in
``app.tasks`` submodules are auto-discovered so they can be called by name
from anywhere in the codebase.

**For Developers:**
    Import ``celery_app`` when defining tasks::

        from app.tasks.celery_app import celery_app

        @celery_app.task(bind=True, max_retries=3)
        def my_task(self, arg):
            ...

    Start the worker and Beat scheduler in separate terminals::

        celery -A app.tasks.celery_app worker --loglevel=info
        celery -A app.tasks.celery_app beat --loglevel=info

**For QA Engineers:**
    The Beat schedule defines three periodic tasks:
    - ``aggregate-daily-analytics``: Runs at 2:00 AM UTC daily.
    - ``cleanup-old-notifications``: Runs at 3:00 AM UTC daily.
    - ``check-fulfillment-status``: Runs every 30 minutes.

**For Project Managers:**
    Celery handles all background processing: sending emails, delivering
    webhooks, running fraud checks, and automating order fulfillment.
    The Beat scheduler triggers periodic maintenance tasks automatically.
"""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "dropshipping",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # Prevent Celery from overriding the root logger configuration
    worker_hijack_root_logger=False,
    # Beat schedule for periodic tasks
    beat_schedule={
        "aggregate-daily-analytics": {
            "task": "app.tasks.analytics_tasks.aggregate_daily_analytics",
            "schedule": crontab(hour=2, minute=0),
        },
        "cleanup-old-notifications": {
            "task": "app.tasks.analytics_tasks.cleanup_old_notifications",
            "schedule": crontab(hour=3, minute=0),
        },
        "check-fulfillment-status": {
            "task": "app.tasks.order_tasks.check_fulfillment_status",
            "schedule": crontab(minute="*/30"),
        },
    },
)

# Auto-discover task modules inside the app.tasks package
celery_app.autodiscover_tasks(["app.tasks"])
