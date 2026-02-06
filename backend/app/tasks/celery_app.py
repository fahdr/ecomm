"""Celery application instance and configuration.

Creates the shared Celery app used by workers and Beat. Tasks defined in
``app.tasks`` submodules are auto-discovered so they can be called by name
from anywhere in the codebase.

Usage:
    # Start worker
    celery -A app.tasks.celery_app worker --loglevel=info

    # Start Beat scheduler
    celery -A app.tasks.celery_app beat --loglevel=info
"""

from celery import Celery

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
)

# Auto-discover task modules inside the app.tasks package
celery_app.autodiscover_tasks(["app.tasks"])
