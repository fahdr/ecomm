"""
Webhook endpoints for receiving external events.

Handles Stripe webhook events for subscription lifecycle management.

For Developers:
    In mock mode, webhooks accept raw JSON without signature verification.
    In production, Stripe webhook signatures are verified using the
    STRIPE_WEBHOOK_SECRET.

For QA Engineers:
    Test webhook handling by sending mock events to POST /webhooks/stripe.
    Verify subscription state changes after webhook processing.
"""

import json

from fastapi import APIRouter, HTTPException, Request, status

from app.config import settings
from app.database import async_session_factory
from app.services.billing_service import sync_subscription_from_event

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(request: Request):
    """
    Handle incoming Stripe webhook events.

    Processes subscription lifecycle events:
    - customer.subscription.created
    - customer.subscription.updated
    - customer.subscription.deleted

    In mock mode, accepts raw JSON. In production, verifies Stripe signature.

    Args:
        request: The incoming webhook request.

    Returns:
        Dict with status 'ok'.

    Raises:
        HTTPException 400: If signature verification fails or payload is invalid.
    """
    payload = await request.body()

    if settings.stripe_secret_key and settings.stripe_webhook_secret:
        # Production: verify Stripe signature
        import stripe

        sig_header = request.headers.get("stripe-signature")
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
        except (stripe.error.SignatureVerificationError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature",
            )
    else:
        # Mock mode: parse JSON directly
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            )

    event_type = event.get("type", "")
    event_data = event.get("data", {}).get("object", {})

    # Handle subscription events
    if event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        async with async_session_factory() as db:
            try:
                await sync_subscription_from_event(db, event_data)
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    return {"status": "ok"}
