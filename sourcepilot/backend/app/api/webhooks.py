"""
Webhook endpoints for receiving external events.

Handles Stripe webhook events for subscription lifecycle management,
and TrendScout product-scored webhooks for automated imports.

For Developers:
    In mock mode, webhooks accept raw JSON without signature verification.
    In production, Stripe webhook signatures are verified using the
    STRIPE_WEBHOOK_SECRET. The product-scored webhook creates import jobs
    when products exceed a configurable score threshold.

For QA Engineers:
    Test webhook handling by sending mock events to POST /webhooks/stripe.
    Test product-scored webhook with various score values above/below threshold.
    Verify subscription state changes after webhook processing.
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.config import settings
from app.database import async_session_factory, get_db
from app.models.user import User
from app.services.billing_service import sync_subscription_from_event

logger = logging.getLogger(__name__)

# Minimum score threshold to auto-import a product
AUTO_IMPORT_SCORE_THRESHOLD = 50.0

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


# ---------------------------------------------------------------------------
# Product-scored webhook (from TrendScout)
# ---------------------------------------------------------------------------


class ProductScoredPayload(BaseModel):
    """
    Payload for the product-scored webhook from TrendScout.

    Attributes:
        product_url: URL of the product on the supplier platform.
        source: Supplier platform identifier.
        score: TrendScout score for the product (0-100).
        product_name: Display name of the product.
        category: Product category (optional).
    """

    product_url: str = Field(..., min_length=1, description="Product URL on the supplier")
    source: str = Field(..., min_length=1, description="Supplier platform identifier")
    score: float = Field(..., description="TrendScout score (0-100)")
    product_name: str = Field(..., min_length=1, description="Product display name")
    category: str | None = Field(None, description="Product category")


@router.post("/product-scored")
async def product_scored_webhook(
    payload: ProductScoredPayload,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Receive a product-scored event from TrendScout.

    When a product's score exceeds the auto-import threshold, an import
    job is automatically created. Below-threshold products are acknowledged
    but not imported.

    Args:
        payload: Product score data from TrendScout.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Dict with status, whether an import was triggered, and details.
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    db_session: AsyncSession = db

    triggered = payload.score >= AUTO_IMPORT_SCORE_THRESHOLD

    if triggered:
        # Create an import job for high-scoring products
        from app.models.import_job import ImportJob, ImportJobStatus, ImportSource

        try:
            source_enum = ImportSource(payload.source)
        except ValueError:
            source_enum = ImportSource.aliexpress

        import_job = ImportJob(
            user_id=current_user.id,
            source=source_enum,
            source_url=payload.product_url,
            status=ImportJobStatus.pending,
            config={
                "auto_import": True,
                "trendscout_score": payload.score,
                "product_name": payload.product_name,
                "category": payload.category,
            },
        )
        db_session.add(import_job)
        await db_session.flush()

        logger.info(
            "Auto-import triggered for product '%s' (score=%.1f, job_id=%s)",
            payload.product_name,
            payload.score,
            import_job.id,
        )

        return {
            "status": "accepted",
            "import_triggered": True,
            "import_job_id": str(import_job.id),
            "score": payload.score,
        }

    logger.info(
        "Product '%s' scored %.1f (below threshold %.1f), skipped import",
        payload.product_name,
        payload.score,
        AUTO_IMPORT_SCORE_THRESHOLD,
    )

    return {
        "status": "accepted",
        "import_triggered": False,
        "score": payload.score,
    }
