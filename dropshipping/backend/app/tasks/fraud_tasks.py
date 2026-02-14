"""Fraud detection Celery tasks.

Automatically scores orders for fraud risk using heuristic signals.
High-risk orders are flagged for manual review and trigger dashboard
notifications.

**For Developers:**
    The scoring logic mirrors ``fraud_service.check_order_fraud()`` but
    runs synchronously in the Celery worker. Five heuristic signals
    contribute to a 0-100 risk score. The task creates a ``FraudCheck``
    record and dispatches a notification task if the order is flagged.

**For QA Engineers:**
    - Signals and their point values:
      - ``high_amount`` (>= $500): +20 points
      - ``new_customer_high_order`` (first order >= $200): +25 points
      - ``velocity_spike`` (3+ orders from same email in 1 hour): +30 points
      - ``suspicious_email`` (contains "+", "test", "fake", "temp"): +15 points
      - ``first_order`` (no previous paid orders): +10 points
    - Risk levels: low (0-25), medium (26-50), high (51-75), critical (76-100).
    - Orders at ``high`` or ``critical`` risk are auto-flagged.

**For Project Managers:**
    This task powers the automated fraud detection system (Feature 28),
    running automatically on every paid order to catch suspicious activity
    before fulfillment.

**For End Users:**
    Every order is automatically checked for fraud indicators. Suspicious
    orders are flagged and you'll receive a notification to review them
    before shipping -- protecting your business from chargebacks.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func

from app.tasks.celery_app import celery_app
from app.tasks.db import SyncSessionFactory

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.fraud_tasks.run_fraud_check",
    max_retries=2,
    default_retry_delay=15,
)
def run_fraud_check(self, order_id: str) -> dict:
    """Run an automated fraud risk assessment on an order.

    Evaluates five heuristic signals, calculates a composite risk score,
    creates a ``FraudCheck`` record, and dispatches a notification if the
    order is flagged.

    Args:
        order_id: UUID string of the order to assess.

    Returns:
        Dict with ``fraud_check_id``, ``risk_score``, ``risk_level``,
        ``is_flagged``, and ``signals`` keys.
    """
    from app.models.fraud import FraudCheck, FraudRiskLevel
    from app.models.order import Order, OrderStatus

    session = SyncSessionFactory()
    try:
        order = session.query(Order).filter(Order.id == uuid.UUID(order_id)).first()
        if not order:
            return {"status": "skipped", "reason": "Order not found"}

        signals = []
        score = 0

        # Signal 1: High order amount (>= $500)
        if order.total >= Decimal("500"):
            signals.append("high_amount")
            score += 20

        # Signal 2: New customer with high order (first order >= $200)
        previous_orders = (
            session.query(func.count(Order.id))
            .filter(
                Order.customer_email == order.customer_email,
                Order.store_id == order.store_id,
                Order.status.in_([OrderStatus.paid, OrderStatus.shipped, OrderStatus.delivered]),
                Order.id != order.id,
            )
            .scalar()
        )
        is_first_order = (previous_orders or 0) == 0

        if is_first_order and order.total >= Decimal("200"):
            signals.append("new_customer_high_order")
            score += 25

        # Signal 3: Velocity spike (3+ orders from same email in 1 hour)
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_orders = (
            session.query(func.count(Order.id))
            .filter(
                Order.customer_email == order.customer_email,
                Order.store_id == order.store_id,
                Order.created_at >= one_hour_ago,
            )
            .scalar()
        )
        if (recent_orders or 0) >= 3:
            signals.append("velocity_spike")
            score += 30

        # Signal 4: Suspicious email patterns
        email_lower = order.customer_email.lower()
        suspicious_patterns = ["+", "test", "fake", "temp"]
        if any(pattern in email_lower for pattern in suspicious_patterns):
            signals.append("suspicious_email")
            score += 15

        # Signal 5: First order (mild risk signal)
        if is_first_order:
            signals.append("first_order")
            score += 10

        # Cap score at 100
        score = min(score, 100)

        # Determine risk level
        if score <= 25:
            risk_level = FraudRiskLevel.low
        elif score <= 50:
            risk_level = FraudRiskLevel.medium
        elif score <= 75:
            risk_level = FraudRiskLevel.high
        else:
            risk_level = FraudRiskLevel.critical

        is_flagged = risk_level in (FraudRiskLevel.high, FraudRiskLevel.critical)

        # Create fraud check record
        fraud_check = FraudCheck(
            store_id=order.store_id,
            order_id=order.id,
            risk_level=risk_level,
            risk_score=Decimal(str(score)),
            signals=signals,
            is_flagged=is_flagged,
        )
        session.add(fraud_check)
        session.commit()
        session.refresh(fraud_check)

        logger.info(
            "FRAUD CHECK: order=%s score=%d level=%s flagged=%s signals=%s",
            order_id[:8], score, risk_level.value, is_flagged, signals,
        )

        # Dispatch fraud alert notification if flagged
        if is_flagged:
            from app.tasks.notification_tasks import create_fraud_alert_notification
            create_fraud_alert_notification.delay(
                str(order.store_id), str(fraud_check.id)
            )

        return {
            "fraud_check_id": str(fraud_check.id),
            "risk_score": score,
            "risk_level": risk_level.value,
            "is_flagged": is_flagged,
            "signals": signals,
        }
    except Exception as exc:
        session.rollback()
        logger.error("run_fraud_check failed: %s", exc)
        raise self.retry(exc=exc)
    finally:
        session.close()
