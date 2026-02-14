"""In-app notification Celery tasks.

Creates dashboard notifications for store owners when business events
occur. Notifications appear in the bell icon on the dashboard and link
to the relevant page.

**For Developers:**
    Each task creates a ``Notification`` row with the appropriate type,
    title, message, action URL, and metadata. The ``user_id`` is resolved
    from the store's owner. Tasks use the sync session factory.

**For QA Engineers:**
    - Notification types match the ``NotificationType`` enum values.
    - ``action_url`` deep-links to the relevant dashboard page.
    - ``metadata_`` stores structured event data for rich rendering.
    - If the store or related entity is not found, the task skips
      without raising an error.

**For Project Managers:**
    These tasks power the notification system (Feature 25), automatically
    informing store owners about orders, reviews, stock levels, and
    security alerts.

**For End Users:**
    You'll see real-time notifications in your dashboard when new orders
    come in, customers leave reviews, stock runs low, or potential fraud
    is detected -- keeping you informed without having to constantly
    refresh the page.
"""

import logging
import uuid

from app.tasks.celery_app import celery_app
from app.tasks.db import SyncSessionFactory

logger = logging.getLogger(__name__)


def _get_store_owner_id(session, store_id: str) -> uuid.UUID | None:
    """Resolve the store owner's user_id from a store_id.

    Args:
        session: A sync SQLAlchemy session.
        store_id: UUID string of the store.

    Returns:
        The owner's user_id UUID, or None if the store is not found.
    """
    from app.models.store import Store
    store = session.query(Store).filter(Store.id == uuid.UUID(store_id)).first()
    return store.user_id if store else None


@celery_app.task(
    bind=True,
    name="app.tasks.notification_tasks.create_order_notification",
    max_retries=2,
    default_retry_delay=10,
)
def create_order_notification(self, store_id: str, order_id: str, event_type: str) -> dict:
    """Create a dashboard notification for an order lifecycle event.

    Args:
        store_id: UUID string of the store.
        order_id: UUID string of the order.
        event_type: One of ``"order_placed"``, ``"order_shipped"``,
            ``"order_delivered"``.

    Returns:
        Dict with ``status`` and ``notification_id`` keys.
    """
    from app.models.notification import Notification, NotificationType
    from app.models.order import Order

    session = SyncSessionFactory()
    try:
        user_id = _get_store_owner_id(session, store_id)
        if not user_id:
            return {"status": "skipped", "reason": "Store not found"}

        order = session.query(Order).filter(Order.id == uuid.UUID(order_id)).first()
        if not order:
            return {"status": "skipped", "reason": "Order not found"}

        # Map event_type to notification content
        content_map = {
            "order_placed": {
                "type": NotificationType.order_placed,
                "title": "New Order Received",
                "message": f"Order #{str(order.id)[:8]} for ${order.total} from {order.customer_email}",
            },
            "order_shipped": {
                "type": NotificationType.order_shipped,
                "title": "Order Shipped",
                "message": f"Order #{str(order.id)[:8]} has been shipped to {order.customer_email}",
            },
            "order_delivered": {
                "type": NotificationType.order_delivered,
                "title": "Order Delivered",
                "message": f"Order #{str(order.id)[:8]} has been delivered to {order.customer_email}",
            },
        }

        content = content_map.get(event_type)
        if not content:
            return {"status": "skipped", "reason": f"Unknown event_type: {event_type}"}

        notification = Notification(
            user_id=user_id,
            store_id=uuid.UUID(store_id),
            notification_type=content["type"],
            title=content["title"],
            message=content["message"],
            action_url=f"/stores/{store_id}/orders/{order_id}",
            metadata_={"order_id": order_id, "total": str(order.total), "event": event_type},
        )
        session.add(notification)
        session.commit()
        session.refresh(notification)

        logger.info(
            "NOTIFICATION: %s for order=%s store=%s",
            event_type, order_id[:8], store_id[:8],
        )
        return {"status": "created", "notification_id": str(notification.id)}
    except Exception as exc:
        session.rollback()
        logger.error("create_order_notification failed: %s", exc)
        raise self.retry(exc=exc)
    finally:
        session.close()


@celery_app.task(
    bind=True,
    name="app.tasks.notification_tasks.create_review_notification",
    max_retries=2,
    default_retry_delay=10,
)
def create_review_notification(self, store_id: str, review_id: str) -> dict:
    """Create a dashboard notification when a new review is posted.

    Args:
        store_id: UUID string of the store.
        review_id: UUID string of the review.

    Returns:
        Dict with ``status`` and ``notification_id`` keys.
    """
    from app.models.notification import Notification, NotificationType
    from app.models.review import Review

    session = SyncSessionFactory()
    try:
        user_id = _get_store_owner_id(session, store_id)
        if not user_id:
            return {"status": "skipped", "reason": "Store not found"}

        review = session.query(Review).filter(Review.id == uuid.UUID(review_id)).first()
        if not review:
            return {"status": "skipped", "reason": "Review not found"}

        notification = Notification(
            user_id=user_id,
            store_id=uuid.UUID(store_id),
            notification_type=NotificationType.review_received,
            title="New Review Posted",
            message=f"{'★' * review.rating} review on {review.product_title if hasattr(review, 'product_title') else 'a product'}",
            action_url=f"/stores/{store_id}/reviews",
            metadata_={"review_id": review_id, "rating": review.rating},
        )
        session.add(notification)
        session.commit()
        session.refresh(notification)

        logger.info("NOTIFICATION: review=%s store=%s", review_id[:8], store_id[:8])
        return {"status": "created", "notification_id": str(notification.id)}
    except Exception as exc:
        session.rollback()
        logger.error("create_review_notification failed: %s", exc)
        raise self.retry(exc=exc)
    finally:
        session.close()


@celery_app.task(
    bind=True,
    name="app.tasks.notification_tasks.create_low_stock_notification",
    max_retries=2,
    default_retry_delay=10,
)
def create_low_stock_notification(self, store_id: str, product_id: str, variant_id: str) -> dict:
    """Create a dashboard notification for a low-stock product variant.

    Args:
        store_id: UUID string of the store.
        product_id: UUID string of the product.
        variant_id: UUID string of the low-stock variant.

    Returns:
        Dict with ``status`` and ``notification_id`` keys.
    """
    from app.models.notification import Notification, NotificationType
    from app.models.product import Product, ProductVariant

    session = SyncSessionFactory()
    try:
        user_id = _get_store_owner_id(session, store_id)
        if not user_id:
            return {"status": "skipped", "reason": "Store not found"}

        product = session.query(Product).filter(Product.id == uuid.UUID(product_id)).first()
        variant = session.query(ProductVariant).filter(ProductVariant.id == uuid.UUID(variant_id)).first()

        product_title = product.title if product else "Unknown Product"
        variant_name = variant.name if variant else "Unknown Variant"
        stock = variant.inventory_count if variant else 0

        notification = Notification(
            user_id=user_id,
            store_id=uuid.UUID(store_id),
            notification_type=NotificationType.low_stock,
            title="Low Stock Alert",
            message=f"{product_title} ({variant_name}) has only {stock} units left",
            action_url=f"/stores/{store_id}/products/{product_id}",
            metadata_={
                "product_id": product_id,
                "variant_id": variant_id,
                "inventory_count": stock,
            },
        )
        session.add(notification)
        session.commit()
        session.refresh(notification)

        logger.info(
            "NOTIFICATION: low_stock product=%s variant=%s stock=%d",
            product_id[:8], variant_id[:8], stock,
        )
        return {"status": "created", "notification_id": str(notification.id)}
    except Exception as exc:
        session.rollback()
        logger.error("create_low_stock_notification failed: %s", exc)
        raise self.retry(exc=exc)
    finally:
        session.close()


@celery_app.task(
    bind=True,
    name="app.tasks.notification_tasks.create_fraud_alert_notification",
    max_retries=2,
    default_retry_delay=10,
)
def create_fraud_alert_notification(self, store_id: str, fraud_check_id: str) -> dict:
    """Create a dashboard notification when fraud is detected on an order.

    Args:
        store_id: UUID string of the store.
        fraud_check_id: UUID string of the fraud check.

    Returns:
        Dict with ``status`` and ``notification_id`` keys.
    """
    from app.models.fraud import FraudCheck
    from app.models.notification import Notification, NotificationType

    session = SyncSessionFactory()
    try:
        user_id = _get_store_owner_id(session, store_id)
        if not user_id:
            return {"status": "skipped", "reason": "Store not found"}

        fc = session.query(FraudCheck).filter(FraudCheck.id == uuid.UUID(fraud_check_id)).first()
        if not fc:
            return {"status": "skipped", "reason": "Fraud check not found"}

        notification = Notification(
            user_id=user_id,
            store_id=uuid.UUID(store_id),
            notification_type=NotificationType.system,
            title=f"Fraud Alert: {fc.risk_level.value.title()} Risk Order",
            message=f"Order #{str(fc.order_id)[:8]} scored {fc.risk_score}/100 — review before fulfilling",
            action_url=f"/stores/{store_id}/fraud",
            metadata_={
                "fraud_check_id": fraud_check_id,
                "order_id": str(fc.order_id),
                "risk_score": float(fc.risk_score),
                "risk_level": fc.risk_level.value,
            },
        )
        session.add(notification)
        session.commit()
        session.refresh(notification)

        logger.info(
            "NOTIFICATION: fraud_alert order=%s risk=%s score=%s",
            str(fc.order_id)[:8], fc.risk_level.value, fc.risk_score,
        )
        return {"status": "created", "notification_id": str(notification.id)}
    except Exception as exc:
        session.rollback()
        logger.error("create_fraud_alert_notification failed: %s", exc)
        raise self.retry(exc=exc)
    finally:
        session.close()
