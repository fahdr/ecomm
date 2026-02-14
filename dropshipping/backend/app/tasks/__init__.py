"""Celery task package for the dropshipping platform.

This package contains the Celery app instance (``celery_app``) and all
background task modules. Tasks are auto-discovered by Celery when the
worker starts.

**Modules:**
    - ``celery_app``: Celery configuration and Beat schedule.
    - ``db``: Synchronous session factory for task DB access.
    - ``email_tasks``: Transactional email dispatch tasks.
    - ``webhook_tasks``: Store webhook HTTP delivery tasks.
    - ``notification_tasks``: In-app notification creation tasks.
    - ``fraud_tasks``: Automated fraud scoring tasks.
    - ``order_tasks``: Order processing orchestration tasks.
    - ``analytics_tasks``: Periodic analytics and cleanup tasks.
"""
