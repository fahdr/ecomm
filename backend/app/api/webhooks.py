"""Webhook API router for third-party integrations.

Handles incoming webhooks from external services like Stripe.
These endpoints do not require JWT authentication but verify
requests using service-specific signature validation.

**For Developers:**
    The Stripe webhook endpoint reads the raw request body and
    verifies the ``Stripe-Signature`` header before processing.
    The ``checkout.session.completed`` event triggers order confirmation.

**For QA Engineers:**
    - Stripe webhook requires a valid signature header.
    - Only ``checkout.session.completed`` events are processed.
    - A confirmed order transitions from ``pending`` to ``paid``.
    - Invalid signatures return 400. Missing config returns 400.

**For End Users:**
    Webhooks are internal communication channels between payment
    providers and the platform. They run automatically when you
    make a payment.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import order_service
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
    Currently handles ``checkout.session.completed`` to confirm orders.

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

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        stripe_session_id = session["id"]

        order = await order_service.confirm_order(db, stripe_session_id)
        if order:
            logger.info("Order %s confirmed via Stripe webhook", order.id)
        else:
            logger.warning(
                "No pending order found for Stripe session %s",
                stripe_session_id,
            )

    return {"status": "ok"}
