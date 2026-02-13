"""Order processing Celery tasks.

Orchestrates post-payment workflows including fraud detection, email
dispatch, webhook delivery, notification creation, low-stock checks,
and automatic supplier fulfillment.

**For Developers:**
    ``process_paid_order`` is the main orchestrator triggered by the
    Stripe webhook handler. It coordinates all downstream tasks:
    fraud check (sync call), then fan-out email, webhook, notification,
    low-stock alert, and auto-fulfillment tasks via ``.delay()``.

    ``auto_fulfill_order`` checks if all order items have a primary
    supplier and transitions the order to ``shipped`` with a mock
    tracking number (dev mode).

    ``check_fulfillment_status`` is a Beat task (every 30 min) that
    simulates tracking updates by transitioning shipped orders to
    delivered after 7+ days.

**For QA Engineers:**
    - ``process_paid_order`` always runs the fraud check synchronously
      (not ``.delay()``) because the result determines whether to
      auto-fulfill.
    - Low-stock threshold is 5 units per variant.
    - ``auto_fulfill_order`` only transitions orders that are still in
      ``paid`` status (prevents double-fulfillment).
    - ``check_fulfillment_status`` uses a random 30% chance per order
      in dev mode to simulate delivery.

**For Project Managers:**
    These tasks form the core dropshipping automation loop (Feature 10
    enhancement): payment confirmed → fraud check → email + webhook +
    notification → auto-fulfill → track → deliver. This is the heart
    of the "minimal manual intervention" promise.

**For End Users:**
    When a customer pays for an order, the system automatically checks
    for fraud, sends a confirmation email, notifies you on your dashboard,
    and (if you've configured suppliers) starts the fulfillment process
    automatically. You'll receive shipping updates without lifting a finger.
"""

import logging
import random
import uuid
from datetime import datetime, timedelta, timezone

from app.tasks.celery_app import celery_app
from app.tasks.db import SyncSessionFactory

logger = logging.getLogger(__name__)

LOW_STOCK_THRESHOLD = 5


@celery_app.task(
    bind=True,
    name="app.tasks.order_tasks.process_paid_order",
    max_retries=2,
    default_retry_delay=30,
)
def process_paid_order(self, order_id: str) -> dict:
    """Orchestrate all post-payment processing for an order.

    This is the main entry point called from the Stripe webhook handler
    after an order transitions to ``paid``. It coordinates:

    1. Fraud check (synchronous — result needed for fulfillment decision)
    2. Order confirmation email
    3. Webhook dispatch (``order.paid``)
    4. Dashboard notification (``order_placed``)
    5. Low-stock alerts for variants with <= 5 units
    6. Auto-fulfillment (if not fraud-flagged and suppliers configured)

    Args:
        order_id: UUID string of the paid order.

    Returns:
        Dict with processing results including fraud status.
    """
    from app.models.order import Order, OrderItem, OrderStatus
    from app.models.product import ProductVariant
    from app.tasks.email_tasks import send_low_stock_alert, send_order_confirmation
    from app.tasks.notification_tasks import (
        create_low_stock_notification,
        create_order_notification,
    )
    from app.tasks.webhook_tasks import dispatch_webhook_event

    session = SyncSessionFactory()
    try:
        order = session.query(Order).filter(Order.id == uuid.UUID(order_id)).first()
        if not order:
            return {"status": "skipped", "reason": "Order not found"}

        if order.status != OrderStatus.paid:
            return {"status": "skipped", "reason": f"Order status is {order.status.value}, not paid"}

        store_id = str(order.store_id)
        result = {"order_id": order_id, "store_id": store_id}

        # 1. Run fraud check synchronously (need result for auto-fulfill decision)
        from app.tasks.fraud_tasks import run_fraud_check
        fraud_result = run_fraud_check(order_id)
        result["fraud"] = fraud_result

        # 2. Send order confirmation email
        send_order_confirmation.delay(order_id)

        # 3. Dispatch webhook event
        dispatch_webhook_event.delay(store_id, "order.paid", {
            "order_id": order_id,
            "customer_email": order.customer_email,
            "total": str(order.total),
            "currency": order.currency,
        })

        # 4. Create dashboard notification
        create_order_notification.delay(store_id, order_id, "order_placed")

        # 5. Check for low-stock variants
        order_items = (
            session.query(OrderItem)
            .filter(OrderItem.order_id == order.id)
            .all()
        )
        low_stock_variants = []
        for item in order_items:
            if item.variant_id:
                variant = (
                    session.query(ProductVariant)
                    .filter(ProductVariant.id == item.variant_id)
                    .first()
                )
                if variant and variant.inventory_count <= LOW_STOCK_THRESHOLD:
                    low_stock_variants.append(variant)
                    send_low_stock_alert.delay(
                        store_id, str(item.product_id), str(variant.id)
                    )
                    create_low_stock_notification.delay(
                        store_id, str(item.product_id), str(variant.id)
                    )
        result["low_stock_alerts"] = len(low_stock_variants)

        # 6. Auto-fulfill if not fraud-flagged
        is_flagged = fraud_result.get("is_flagged", False) if isinstance(fraud_result, dict) else False
        if not is_flagged:
            auto_fulfill_order.delay(order_id)
            result["auto_fulfill"] = "dispatched"
        else:
            result["auto_fulfill"] = "skipped_fraud_flagged"

        logger.info(
            "PROCESS ORDER: order=%s fraud=%s low_stock=%d auto_fulfill=%s",
            order_id[:8],
            fraud_result.get("risk_level", "unknown") if isinstance(fraud_result, dict) else "error",
            len(low_stock_variants),
            result["auto_fulfill"],
        )
        return result
    except Exception as exc:
        logger.error("process_paid_order failed: %s", exc)
        raise self.retry(exc=exc)
    finally:
        session.close()


@celery_app.task(
    bind=True,
    name="app.tasks.order_tasks.auto_fulfill_order",
    max_retries=2,
    default_retry_delay=30,
)
def auto_fulfill_order(self, order_id: str) -> dict:
    """Attempt automatic fulfillment by checking supplier availability.

    Checks if all order items have a primary active supplier. If so,
    transitions the order to ``shipped`` with a mock tracking number
    (in dev mode) and dispatches shipped notifications.

    Args:
        order_id: UUID string of the order.

    Returns:
        Dict with ``status`` and fulfillment details.
    """
    from app.models.order import Order, OrderItem, OrderStatus
    from app.models.supplier import ProductSupplier, Supplier, SupplierStatus
    from app.tasks.email_tasks import send_order_shipped
    from app.tasks.notification_tasks import create_order_notification
    from app.tasks.webhook_tasks import dispatch_webhook_event

    session = SyncSessionFactory()
    try:
        order = session.query(Order).filter(Order.id == uuid.UUID(order_id)).first()
        if not order:
            return {"status": "skipped", "reason": "Order not found"}

        if order.status != OrderStatus.paid:
            return {"status": "skipped", "reason": f"Order status is {order.status.value}, not paid"}

        store_id = str(order.store_id)

        # Check if all items have primary active suppliers
        order_items = (
            session.query(OrderItem)
            .filter(OrderItem.order_id == order.id)
            .all()
        )

        if not order_items:
            return {"status": "skipped", "reason": "No order items"}

        all_have_supplier = True
        for item in order_items:
            if not item.product_id:
                all_have_supplier = False
                break

            primary_supplier = (
                session.query(ProductSupplier)
                .join(Supplier, ProductSupplier.supplier_id == Supplier.id)
                .filter(
                    ProductSupplier.product_id == item.product_id,
                    ProductSupplier.is_primary.is_(True),
                    Supplier.status == SupplierStatus.active,
                )
                .first()
            )
            if not primary_supplier:
                all_have_supplier = False
                break

        if not all_have_supplier:
            logger.info(
                "AUTO-FULFILL: skipped order=%s — not all items have primary suppliers",
                order_id[:8],
            )
            return {"status": "skipped", "reason": "Not all items have primary suppliers"}

        # Fulfill the order (dev mode: mock tracking number)
        tracking_number = f"TRK-{uuid.uuid4().hex[:12].upper()}"
        order.status = OrderStatus.shipped
        order.tracking_number = tracking_number
        order.carrier = "Auto-Fulfill"
        order.shipped_at = datetime.now(timezone.utc)
        session.commit()

        # Dispatch shipped notifications
        send_order_shipped.delay(order_id, tracking_number)
        dispatch_webhook_event.delay(store_id, "order.shipped", {
            "order_id": order_id,
            "tracking_number": tracking_number,
            "carrier": "Auto-Fulfill",
        })
        create_order_notification.delay(store_id, order_id, "order_shipped")

        logger.info(
            "AUTO-FULFILL: order=%s tracking=%s",
            order_id[:8], tracking_number,
        )
        return {
            "status": "fulfilled",
            "tracking_number": tracking_number,
            "carrier": "Auto-Fulfill",
        }
    except Exception as exc:
        session.rollback()
        logger.error("auto_fulfill_order failed: %s", exc)
        raise self.retry(exc=exc)
    finally:
        session.close()


@celery_app.task(
    name="app.tasks.order_tasks.check_fulfillment_status",
)
def check_fulfillment_status() -> dict:
    """Check shipped orders for delivery status updates (Beat task).

    Runs every 30 minutes via Celery Beat. In dev mode, simulates
    tracking updates by randomly transitioning orders shipped 7+ days
    ago to ``delivered`` (30% chance per order per check).

    In production, this would poll supplier tracking APIs for real
    status updates.

    Returns:
        Dict with ``checked_count`` and ``delivered_count`` keys.
    """
    from app.models.order import Order, OrderStatus
    from app.tasks.email_tasks import send_order_delivered
    from app.tasks.notification_tasks import create_order_notification
    from app.tasks.webhook_tasks import dispatch_webhook_event

    session = SyncSessionFactory()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)

        shipped_orders = (
            session.query(Order)
            .filter(
                Order.status == OrderStatus.shipped,
                Order.shipped_at.isnot(None),
                Order.shipped_at <= cutoff,
            )
            .all()
        )

        checked = len(shipped_orders)
        delivered = 0

        for order in shipped_orders:
            # Dev mode: 30% chance of delivery per check
            if random.random() < 0.3:
                order.status = OrderStatus.delivered
                order.delivered_at = datetime.now(timezone.utc)
                delivered += 1

                order_id = str(order.id)
                store_id = str(order.store_id)

                send_order_delivered.delay(order_id)
                dispatch_webhook_event.delay(store_id, "order.delivered", {
                    "order_id": order_id,
                })
                create_order_notification.delay(store_id, order_id, "order_delivered")

        if delivered > 0:
            session.commit()

        logger.info(
            "FULFILLMENT CHECK: checked=%d delivered=%d",
            checked, delivered,
        )
        return {"checked_count": checked, "delivered_count": delivered}
    except Exception as exc:
        session.rollback()
        logger.error("check_fulfillment_status failed: %s", exc)
        return {"error": str(exc)}
    finally:
        session.close()
