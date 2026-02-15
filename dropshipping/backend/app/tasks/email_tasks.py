"""Email dispatch Celery tasks.

Queues transactional emails for asynchronous delivery. Each task loads
the relevant entity from the database, builds an email context, and
delegates to ``EmailService`` for rendering and sending.

**For Developers:**
    All tasks use the sync session factory (``SyncSessionFactory``) because
    Celery workers run synchronously. Entity IDs are passed as strings and
    converted to ``uuid.UUID`` inside the task body (Celery uses JSON
    serialization). Tasks retry up to 3 times on failure with a 30-second
    delay between attempts.

**For QA Engineers:**
    - In dev mode, emails are logged to stdout (not actually sent).
    - Tasks return a dict with ``status`` ("sent" or "skipped") and
      the recipient ``email``.
    - If the entity is not found, the task returns ``status: "skipped"``
      without raising an error or retrying.

**For Project Managers:**
    These tasks power the transactional email system (Feature 11). They
    ensure that customers and team members receive timely notifications
    without blocking API request handlers.

**For End Users:**
    Emails for order confirmations, shipping updates, refund notifications,
    and more are sent automatically in the background so your dashboard
    stays responsive while your customers are kept informed.
"""

import logging
import uuid

from app.tasks.celery_app import celery_app
from app.tasks.db import SyncSessionFactory

logger = logging.getLogger(__name__)


def _get_email_service():
    """Lazy-import EmailService to avoid circular imports.

    Returns:
        An ``EmailService`` instance.
    """
    from app.services.email_service import EmailService
    return EmailService()


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_order_confirmation",
    max_retries=3,
    default_retry_delay=30,
)
def send_order_confirmation(self, order_id: str) -> dict:
    """Send an order confirmation email after payment.

    Args:
        order_id: UUID string of the paid order.

    Returns:
        Dict with ``status`` and ``email`` keys.
    """
    from app.models.order import Order
    from app.models.store import Store

    session = SyncSessionFactory()
    try:
        order = session.query(Order).filter(Order.id == uuid.UUID(order_id)).first()
        if not order:
            return {"status": "skipped", "reason": "Order not found"}

        store = session.query(Store).filter(Store.id == order.store_id).first()
        if not store:
            return {"status": "skipped", "reason": "Store not found"}

        svc = _get_email_service()
        context = {
            "store_name": store.name,
            "order_id": str(order.id),
            "order_total": str(order.total),
            "customer_email": order.customer_email,
            "items": [
                {
                    "title": item.product_title,
                    "quantity": item.quantity,
                    "price": str(item.unit_price),
                }
                for item in order.items
            ],
        }
        svc._render_template("order_confirmation.html", context)
        logger.info(
            "EMAIL: order_confirmation to=%s order=%s store=%s",
            order.customer_email, order_id[:8], store.name,
        )
        return {"status": "sent", "email": order.customer_email}
    except Exception as exc:
        logger.error("send_order_confirmation failed: %s", exc)
        raise self.retry(exc=exc)
    finally:
        session.close()


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_order_shipped",
    max_retries=3,
    default_retry_delay=30,
)
def send_order_shipped(self, order_id: str, tracking_number: str | None = None) -> dict:
    """Send a shipping notification email to the customer.

    Args:
        order_id: UUID string of the shipped order.
        tracking_number: Optional tracking number.

    Returns:
        Dict with ``status`` and ``email`` keys.
    """
    from app.models.order import Order
    from app.models.store import Store

    session = SyncSessionFactory()
    try:
        order = session.query(Order).filter(Order.id == uuid.UUID(order_id)).first()
        if not order:
            return {"status": "skipped", "reason": "Order not found"}

        store = session.query(Store).filter(Store.id == order.store_id).first()
        if not store:
            return {"status": "skipped", "reason": "Store not found"}

        svc = _get_email_service()
        context = {
            "store_name": store.name,
            "order_id": str(order.id),
            "customer_email": order.customer_email,
            "tracking_number": tracking_number or order.tracking_number,
        }
        svc._render_template("order_shipped.html", context)
        logger.info(
            "EMAIL: order_shipped to=%s order=%s tracking=%s",
            order.customer_email, order_id[:8], tracking_number,
        )
        return {"status": "sent", "email": order.customer_email}
    except Exception as exc:
        logger.error("send_order_shipped failed: %s", exc)
        raise self.retry(exc=exc)
    finally:
        session.close()


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_order_delivered",
    max_retries=3,
    default_retry_delay=30,
)
def send_order_delivered(self, order_id: str) -> dict:
    """Send a delivery confirmation email to the customer.

    Args:
        order_id: UUID string of the delivered order.

    Returns:
        Dict with ``status`` and ``email`` keys.
    """
    from app.models.order import Order
    from app.models.store import Store

    session = SyncSessionFactory()
    try:
        order = session.query(Order).filter(Order.id == uuid.UUID(order_id)).first()
        if not order:
            return {"status": "skipped", "reason": "Order not found"}

        store = session.query(Store).filter(Store.id == order.store_id).first()
        if not store:
            return {"status": "skipped", "reason": "Store not found"}

        svc = _get_email_service()
        context = {
            "store_name": store.name,
            "order_id": str(order.id),
            "customer_email": order.customer_email,
        }
        svc._render_template("order_delivered.html", context)
        logger.info(
            "EMAIL: order_delivered to=%s order=%s",
            order.customer_email, order_id[:8],
        )
        return {"status": "sent", "email": order.customer_email}
    except Exception as exc:
        logger.error("send_order_delivered failed: %s", exc)
        raise self.retry(exc=exc)
    finally:
        session.close()


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_refund_notification",
    max_retries=3,
    default_retry_delay=30,
)
def send_refund_notification(self, refund_id: str) -> dict:
    """Send a refund confirmation email to the customer.

    Args:
        refund_id: UUID string of the processed refund.

    Returns:
        Dict with ``status`` and ``email`` keys.
    """
    from app.models.refund import Refund
    from app.models.store import Store

    session = SyncSessionFactory()
    try:
        refund = session.query(Refund).filter(Refund.id == uuid.UUID(refund_id)).first()
        if not refund:
            return {"status": "skipped", "reason": "Refund not found"}

        store = session.query(Store).filter(Store.id == refund.store_id).first()
        if not store:
            return {"status": "skipped", "reason": "Store not found"}

        svc = _get_email_service()
        context = {
            "store_name": store.name,
            "refund_amount": str(refund.amount),
            "order_id": str(refund.order_id),
            "customer_email": refund.customer_email,
            "reason": refund.reason.value if hasattr(refund.reason, "value") else str(refund.reason),
        }
        svc._render_template("refund_notification.html", context)
        logger.info(
            "EMAIL: refund_notification to=%s refund=%s amount=%s",
            refund.customer_email, refund_id[:8], refund.amount,
        )
        return {"status": "sent", "email": refund.customer_email}
    except Exception as exc:
        logger.error("send_refund_notification failed: %s", exc)
        raise self.retry(exc=exc)
    finally:
        session.close()


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_welcome_email",
    max_retries=3,
    default_retry_delay=30,
)
def send_welcome_email(self, customer_id: str, store_id: str) -> dict:
    """Send a welcome email to a newly registered customer.

    Args:
        customer_id: UUID string of the new customer.
        store_id: UUID string of the store.

    Returns:
        Dict with ``status`` and ``email`` keys.
    """
    from app.models.customer import CustomerAccount
    from app.models.store import Store

    session = SyncSessionFactory()
    try:
        customer = (
            session.query(CustomerAccount)
            .filter(CustomerAccount.id == uuid.UUID(customer_id))
            .first()
        )
        if not customer:
            return {"status": "skipped", "reason": "Customer not found"}

        store = session.query(Store).filter(Store.id == uuid.UUID(store_id)).first()
        if not store:
            return {"status": "skipped", "reason": "Store not found"}

        svc = _get_email_service()
        context = {
            "store_name": store.name,
            "customer_name": customer.name or customer.email,
            "customer_email": customer.email,
        }
        svc._render_template("welcome.html", context)
        logger.info(
            "EMAIL: welcome to=%s store=%s",
            customer.email, store.name,
        )
        return {"status": "sent", "email": customer.email}
    except Exception as exc:
        logger.error("send_welcome_email failed: %s", exc)
        raise self.retry(exc=exc)
    finally:
        session.close()


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_password_reset",
    max_retries=3,
    default_retry_delay=30,
)
def send_password_reset(self, email: str, reset_token: str, store_id: str | None = None) -> dict:
    """Send a password reset email.

    Args:
        email: The recipient email address.
        reset_token: The password reset token.
        store_id: Optional UUID string of the store for branding.

    Returns:
        Dict with ``status`` and ``email`` keys.
    """
    from app.models.store import Store

    session = SyncSessionFactory()
    try:
        store_name = "Dropship Platform"
        if store_id:
            store = session.query(Store).filter(Store.id == uuid.UUID(store_id)).first()
            if store:
                store_name = store.name

        svc = _get_email_service()
        context = {
            "store_name": store_name,
            "reset_token": reset_token,
            "reset_url": f"/reset-password?token={reset_token}",
            "email": email,
        }
        svc._render_template("password_reset.html", context)
        logger.info("EMAIL: password_reset to=%s", email)
        return {"status": "sent", "email": email}
    except Exception as exc:
        logger.error("send_password_reset failed: %s", exc)
        raise self.retry(exc=exc)
    finally:
        session.close()


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_gift_card_email",
    max_retries=3,
    default_retry_delay=30,
)
def send_gift_card_email(self, gift_card_id: str) -> dict:
    """Send a gift card delivery email.

    Args:
        gift_card_id: UUID string of the gift card.

    Returns:
        Dict with ``status`` and ``email`` keys.
    """
    from app.models.gift_card import GiftCard
    from app.models.store import Store

    session = SyncSessionFactory()
    try:
        gc = session.query(GiftCard).filter(GiftCard.id == uuid.UUID(gift_card_id)).first()
        if not gc:
            return {"status": "skipped", "reason": "Gift card not found"}
        if not gc.customer_email:
            return {"status": "skipped", "reason": "No recipient email"}

        store = session.query(Store).filter(Store.id == gc.store_id).first()
        if not store:
            return {"status": "skipped", "reason": "Store not found"}

        svc = _get_email_service()
        context = {
            "store_name": store.name,
            "gift_card_code": gc.code,
            "balance": str(gc.initial_balance),
            "customer_email": gc.customer_email,
        }
        svc._render_template("gift_card.html", context)
        logger.info(
            "EMAIL: gift_card to=%s code=%s",
            gc.customer_email, gc.code[:6],
        )
        return {"status": "sent", "email": gc.customer_email}
    except Exception as exc:
        logger.error("send_gift_card_email failed: %s", exc)
        raise self.retry(exc=exc)
    finally:
        session.close()


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_team_invite",
    max_retries=3,
    default_retry_delay=30,
)
def send_team_invite(self, invite_id: str, store_id: str) -> dict:
    """Send a team invitation email.

    Args:
        invite_id: UUID string of the team invite.
        store_id: UUID string of the store.

    Returns:
        Dict with ``status`` and ``email`` keys.
    """
    from app.models.store import Store
    from app.models.team import TeamInvite

    session = SyncSessionFactory()
    try:
        invite = (
            session.query(TeamInvite)
            .filter(TeamInvite.id == uuid.UUID(invite_id))
            .first()
        )
        if not invite:
            return {"status": "skipped", "reason": "Invite not found"}

        store = session.query(Store).filter(Store.id == uuid.UUID(store_id)).first()
        if not store:
            return {"status": "skipped", "reason": "Store not found"}

        svc = _get_email_service()
        context = {
            "store_name": store.name,
            "invite_email": invite.email,
            "role": invite.role,
            "invite_url": f"/accept-invite?token={invite.token}",
            "token": invite.token,
        }
        svc._render_template("team_invite.html", context)
        logger.info(
            "EMAIL: team_invite to=%s store=%s role=%s",
            invite.email, store.name, invite.role,
        )
        return {"status": "sent", "email": invite.email}
    except Exception as exc:
        logger.error("send_team_invite failed: %s", exc)
        raise self.retry(exc=exc)
    finally:
        session.close()


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_low_stock_alert",
    max_retries=3,
    default_retry_delay=30,
)
def send_low_stock_alert(self, store_id: str, product_id: str, variant_id: str) -> dict:
    """Send a low stock alert email to the store owner.

    Args:
        store_id: UUID string of the store.
        product_id: UUID string of the product.
        variant_id: UUID string of the low-stock variant.

    Returns:
        Dict with ``status`` and ``email`` keys.
    """
    from app.models.product import Product, ProductVariant
    from app.models.store import Store
    from app.models.user import User

    session = SyncSessionFactory()
    try:
        store = session.query(Store).filter(Store.id == uuid.UUID(store_id)).first()
        if not store:
            return {"status": "skipped", "reason": "Store not found"}

        owner = session.query(User).filter(User.id == store.user_id).first()
        if not owner:
            return {"status": "skipped", "reason": "Store owner not found"}

        product = session.query(Product).filter(Product.id == uuid.UUID(product_id)).first()
        variant = session.query(ProductVariant).filter(ProductVariant.id == uuid.UUID(variant_id)).first()

        svc = _get_email_service()
        context = {
            "store_name": store.name,
            "product_title": product.title if product else "Unknown Product",
            "variant_name": variant.name if variant else "Unknown Variant",
            "inventory_count": variant.inventory_count if variant else 0,
        }
        svc._render_template("low_stock_alert.html", context)
        logger.info(
            "EMAIL: low_stock_alert to=%s product=%s variant=%s stock=%d",
            owner.email, product_id[:8], variant_id[:8],
            variant.inventory_count if variant else 0,
        )
        return {"status": "sent", "email": owner.email}
    except Exception as exc:
        logger.error("send_low_stock_alert failed: %s", exc)
        raise self.retry(exc=exc)
    finally:
        session.close()
