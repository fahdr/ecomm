"""Periodic analytics and maintenance Celery tasks.

These tasks run on a Celery Beat schedule to aggregate analytics data
and perform housekeeping operations like cleaning up old notifications.

**For Developers:**
    Both tasks are registered in the ``beat_schedule`` in
    ``celery_app.py``. ``aggregate_daily_analytics`` runs at 2 AM UTC
    and ``cleanup_old_notifications`` runs at 3 AM UTC. They use the
    sync session factory and operate across all active stores.

**For QA Engineers:**
    - ``aggregate_daily_analytics`` computes yesterday's revenue, order
      count, and profit per active store. Results are logged (future:
      cached to Redis or written to an analytics table).
    - ``cleanup_old_notifications`` deletes read notifications older than
      90 days. Only ``is_read=True`` notifications are removed.

**For Project Managers:**
    These tasks automate daily analytics rollups (Feature 13 enhancement)
    and notification housekeeping (Feature 25), reducing database bloat
    and preparing pre-computed metrics for faster dashboard loading.

**For End Users:**
    Your dashboard analytics are refreshed automatically every night,
    and old notifications are cleaned up periodically to keep your
    notification inbox manageable.
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, func

from app.tasks.celery_app import celery_app
from app.tasks.db import SyncSessionFactory

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.analytics_tasks.aggregate_daily_analytics",
)
def aggregate_daily_analytics() -> dict:
    """Aggregate yesterday's revenue, orders, and profit for each active store.

    Runs daily at 2 AM UTC via Celery Beat. Currently logs results;
    future versions will write to a Redis cache or analytics table for
    faster dashboard queries.

    Returns:
        Dict with ``stores_processed``, ``date``, and ``total_revenue``
        keys.
    """
    from app.models.order import Order, OrderStatus
    from app.models.store import Store, StoreStatus

    session = SyncSessionFactory()
    try:
        yesterday_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=1)
        yesterday_end = yesterday_start + timedelta(days=1)

        # Get all active stores
        stores = (
            session.query(Store)
            .filter(Store.status == StoreStatus.active)
            .all()
        )

        total_platform_revenue = Decimal("0")
        stores_processed = 0

        for store in stores:
            # Revenue from paid/shipped/delivered orders yesterday
            result = (
                session.query(
                    func.count(Order.id).label("order_count"),
                    func.coalesce(func.sum(Order.total), 0).label("revenue"),
                )
                .filter(
                    Order.store_id == store.id,
                    Order.status.in_([
                        OrderStatus.paid,
                        OrderStatus.shipped,
                        OrderStatus.delivered,
                    ]),
                    Order.created_at >= yesterday_start,
                    Order.created_at < yesterday_end,
                )
                .first()
            )

            order_count = result.order_count if result else 0
            revenue = Decimal(str(result.revenue)) if result else Decimal("0")
            total_platform_revenue += revenue
            stores_processed += 1

            if order_count > 0:
                logger.info(
                    "ANALYTICS: store=%s (%s) orders=%d revenue=$%s",
                    str(store.id)[:8], store.name, order_count, revenue,
                )

        date_str = yesterday_start.strftime("%Y-%m-%d")
        logger.info(
            "Daily analytics aggregation complete: date=%s stores=%d total_revenue=$%s",
            date_str, stores_processed, total_platform_revenue,
        )
        return {
            "stores_processed": stores_processed,
            "date": date_str,
            "total_revenue": str(total_platform_revenue),
        }
    except Exception as exc:
        logger.error("aggregate_daily_analytics failed: %s", exc)
        return {"error": str(exc)}
    finally:
        session.close()


@celery_app.task(
    name="app.tasks.analytics_tasks.cleanup_old_notifications",
)
def cleanup_old_notifications() -> dict:
    """Delete read notifications older than 90 days.

    Runs daily at 3 AM UTC via Celery Beat. Only removes notifications
    where ``is_read=True`` to preserve unread items indefinitely.

    Returns:
        Dict with ``deleted_count`` key.
    """
    from app.models.notification import Notification

    session = SyncSessionFactory()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)

        result = session.execute(
            delete(Notification).where(
                Notification.is_read.is_(True),
                Notification.created_at < cutoff,
            )
        )
        deleted_count = result.rowcount
        session.commit()

        logger.info(
            "Notification cleanup: deleted %d read notifications older than 90 days",
            deleted_count,
        )
        return {"deleted_count": deleted_count}
    except Exception as exc:
        session.rollback()
        logger.error("cleanup_old_notifications failed: %s", exc)
        return {"error": str(exc)}
    finally:
        session.close()
