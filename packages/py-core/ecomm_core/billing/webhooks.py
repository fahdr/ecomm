"""
Webhook router factory for Stripe events.

For Developers:
    Use `create_webhook_router(session_factory, plan_limits)`.
    In mock mode, webhooks accept raw JSON without signature verification.
"""

import json

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.ext.asyncio import async_sessionmaker

from ecomm_core.billing.service import sync_subscription_from_event
from ecomm_core.models.user import PlanTier
from ecomm_core.plans import PlanLimits


def create_webhook_router(
    session_factory: async_sessionmaker,
    plan_limits: dict[PlanTier, PlanLimits],
) -> APIRouter:
    """
    Factory to create the webhook router.

    Args:
        session_factory: Async session factory for creating DB sessions.
        plan_limits: Service-specific plan limits for price resolution.

    Returns:
        APIRouter with POST /webhooks/stripe endpoint.
    """
    router = APIRouter(prefix="/webhooks", tags=["webhooks"])

    @router.post("/stripe")
    async def stripe_webhook(request: Request):
        """
        Handle incoming Stripe webhook events.

        Processes subscription lifecycle events:
        - customer.subscription.created
        - customer.subscription.updated
        - customer.subscription.deleted
        """
        from app.config import settings

        payload = await request.body()

        if settings.stripe_secret_key and settings.stripe_webhook_secret:
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
            try:
                event = json.loads(payload)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON payload",
                )

        event_type = event.get("type", "")
        event_data = event.get("data", {}).get("object", {})

        if event_type in (
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        ):
            async with session_factory() as db:
                try:
                    await sync_subscription_from_event(db, event_data, plan_limits)
                    await db.commit()
                except Exception:
                    await db.rollback()
                    raise

        return {"status": "ok"}

    return router
