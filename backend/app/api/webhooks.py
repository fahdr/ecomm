"""Webhook API router for third-party integrations.

Handles incoming webhooks from external services like Stripe.
These endpoints do not require JWT authentication but verify
requests using service-specific signature validation.

**For Developers:**
    The Stripe webhook endpoint reads the raw request body and
    verifies the ``Stripe-Signature`` header before processing.
    Handles both one-time payment events (order confirmation) and
    subscription lifecycle events (created, updated, deleted, payment failed).

**For QA Engineers:**
    - Stripe webhook requires a valid signature header.
    - ``checkout.session.completed`` with ``mode=payment`` confirms orders.
    - ``checkout.session.completed`` with ``mode=subscription`` syncs subscriptions.
    - ``customer.subscription.*`` events sync subscription state.
    - ``invoice.payment_failed`` sets subscription to past_due.
    - Invalid signatures return 400. Missing config returns 400.

**For End Users:**
    Webhooks are internal communication channels between payment
    providers and the platform. They run automatically when you
    make a payment or your subscription status changes.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.store import Store
from app.services import order_service, subscription_service
from app.services.discount_service import apply_discount
from app.services.email_service import email_service
from app.services.stripe_service import construct_webhook_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Handle Stripe webhook events.

    Reads the raw request body and verifies the Stripe signature.
    Routes events to the appropriate service handler based on event type.

    Supported events:
        - ``checkout.session.completed`` (payment mode → order confirmation,
          subscription mode → subscription sync)
        - ``customer.subscription.created`` → subscription sync
        - ``customer.subscription.updated`` → subscription sync
        - ``customer.subscription.deleted`` → subscription sync (revert to free)
        - ``invoice.payment_failed`` → mark subscription as past_due

    Args:
        request: The incoming FastAPI request with raw body.
        db: Async database session injected by FastAPI.

    Returns:
        A dict with ``status: "ok"`` on success.

    Raises:
        HTTPException: 400 if signature verification fails or
            webhook secret is not configured.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = construct_webhook_event(payload, sig_header)
    except ValueError as e:
        logger.error("Stripe webhook config error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook configuration error",
        )
    except Exception as e:
        logger.error("Stripe webhook signature error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    event_type = event["type"]
    event_data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        session_mode = event_data.get("mode", "payment")

        if session_mode == "subscription":
            # Subscription checkout completed — sync via the subscription
            # object (the webhook for customer.subscription.created handles
            # the actual record creation, but we log here for visibility).
            logger.info(
                "Subscription checkout completed for session %s",
                event_data.get("id"),
            )
        else:
            # One-time payment checkout — confirm the order
            stripe_session_id = event_data["id"]
            order = await order_service.confirm_order(db, stripe_session_id)
            if order:
                logger.info("Order %s confirmed via Stripe webhook", order.id)

                # Dispatch post-payment processing via Celery
                # (fraud check, email, webhook, notification, auto-fulfill)
                from app.tasks.order_tasks import process_paid_order
                process_paid_order.delay(str(order.id))

                # Track discount usage if a code was applied
                if order.discount_code and order.discount_amount:
                    try:
                        await apply_discount(
                            db=db,
                            store_id=order.store_id,
                            code=order.discount_code,
                            order_id=order.id,
                            customer_email=order.customer_email,
                            amount_saved=order.discount_amount,
                        )
                    except Exception as disc_err:
                        logger.warning(
                            "Failed to record discount usage for order %s: %s",
                            order.id,
                            disc_err,
                        )
            else:
                logger.warning(
                    "No pending order found for Stripe session %s",
                    stripe_session_id,
                )

    elif event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        sub = await subscription_service.sync_subscription_from_event(db, event_data)
        if sub:
            logger.info(
                "Subscription %s synced: %s → %s",
                sub.stripe_subscription_id,
                event_type,
                sub.status.value,
            )

    elif event_type == "invoice.payment_failed":
        await subscription_service.handle_payment_failed(db, event_data)

    return {"status": "ok"}
