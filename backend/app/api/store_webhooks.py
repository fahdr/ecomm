"""Store Webhooks API router.

Provides endpoints for managing webhook configurations. Store owners can
register webhook URLs to receive real-time notifications about store
events (orders, products, customers, etc.).

**For Developers:**
    The router is nested under stores: ``/stores/{store_id}/webhooks/...``
    (full path: ``/api/v1/stores/{store_id}/webhooks/...``).
    The ``get_current_user`` dependency is used for authentication.
    Service functions in ``store_webhook_service`` handle all business logic.
    This is separate from ``webhooks.py`` which handles incoming Stripe webhooks.

**For QA Engineers:**
    - All endpoints return 401 without a valid token.
    - POST create returns 201 with the webhook configuration.
    - Each webhook has a ``secret`` for payload signature verification.
    - Events: ``order.created``, ``order.updated``, ``product.created``, etc.
    - Delivery history tracks success/failure of webhook calls.
    - DELETE returns 204 with no content.

**For End Users:**
    - Set up webhooks to integrate your store with external systems.
    - Receive real-time notifications about orders, products, and customers.
    - Monitor webhook delivery history to troubleshoot integrations.
"""

import math
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.webhook_config import (
    CreateWebhookRequest,
    PaginatedWebhookResponse,
    UpdateWebhookRequest,
    WebhookDeliveryResponse,
    WebhookResponse,
)

router = APIRouter(prefix="/stores/{store_id}/webhooks", tags=["webhooks-config"])


# ---------------------------------------------------------------------------
# Additional response schemas used only by the API layer
# ---------------------------------------------------------------------------


class PaginatedDeliveryResponse(BaseModel):
    """Paginated list of webhook deliveries.

    Attributes:
        items: List of delivery records.
        total: Total number of deliveries.
        page: Current page number.
        per_page: Number of items per page.
        pages: Total number of pages.
    """

    items: list[WebhookDeliveryResponse]
    total: int
    page: int
    per_page: int
    pages: int


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook_endpoint(
    store_id: uuid.UUID,
    request: CreateWebhookRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WebhookResponse:
    """Create a new webhook configuration for a store.

    Registers a URL to receive HTTP POST notifications for the specified
    event types. A secret key is auto-generated for payload verification.

    Args:
        store_id: The UUID of the store.
        request: Webhook creation payload with URL and events.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        WebhookResponse with the webhook config including the secret.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
        HTTPException 400: If the URL is invalid or events list is empty.
    """
    from app.services import webhook_service as store_webhook_service

    try:
        webhook = await store_webhook_service.create_webhook(
            db,
            store_id=store_id,
            user_id=current_user.id,
            **request.model_dump(),
        )
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_400_BAD_REQUEST
            if "invalid" in detail.lower() or "empty" in detail.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail)
    return WebhookResponse.model_validate(webhook)


@router.get("", response_model=PaginatedWebhookResponse)
async def list_webhooks_endpoint(
    store_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedWebhookResponse:
    """List webhook configurations for a store.

    Args:
        store_id: The UUID of the store.
        page: Page number (1-based, default 1).
        per_page: Items per page (1-100, default 20).
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        PaginatedWebhookResponse with items and pagination metadata.

    Raises:
        HTTPException 404: If the store is not found or belongs to another user.
    """
    from app.services import webhook_service as store_webhook_service

    try:
        all_webhooks = await store_webhook_service.list_webhooks(
            db,
            store_id=store_id,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    total = len(all_webhooks)
    pages = math.ceil(total / per_page) if total > 0 else 1
    offset = (page - 1) * per_page
    webhooks = all_webhooks[offset : offset + per_page]

    return PaginatedWebhookResponse(
        items=[WebhookResponse.model_validate(w) for w in webhooks],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook_endpoint(
    store_id: uuid.UUID,
    webhook_id: uuid.UUID,
    request: UpdateWebhookRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WebhookResponse:
    """Update a webhook configuration (partial update).

    Only provided fields are updated. The secret key is not changeable.

    Args:
        store_id: The UUID of the store.
        webhook_id: The UUID of the webhook to update.
        request: Partial update payload.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        WebhookResponse with the updated webhook data.

    Raises:
        HTTPException 404: If the store or webhook is not found.
    """
    from app.services import webhook_service as store_webhook_service

    try:
        webhook = await store_webhook_service.update_webhook(
            db,
            store_id=store_id,
            user_id=current_user.id,
            webhook_id=webhook_id,
            **request.model_dump(exclude_unset=True),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return WebhookResponse.model_validate(webhook)


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook_endpoint(
    store_id: uuid.UUID,
    webhook_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a webhook configuration and its delivery history.

    Args:
        store_id: The UUID of the store.
        webhook_id: The UUID of the webhook to delete.
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        204 No Content on success.

    Raises:
        HTTPException 404: If the store or webhook is not found.
    """
    from app.services import webhook_service as store_webhook_service

    try:
        await store_webhook_service.delete_webhook(
            db, store_id=store_id, user_id=current_user.id, webhook_id=webhook_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{webhook_id}/deliveries", response_model=PaginatedDeliveryResponse)
async def list_webhook_deliveries_endpoint(
    store_id: uuid.UUID,
    webhook_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedDeliveryResponse:
    """List delivery attempts for a webhook.

    Returns the history of HTTP deliveries for a webhook, including
    request payloads, response status codes, and success/failure flags.

    Args:
        store_id: The UUID of the store.
        webhook_id: The UUID of the webhook.
        page: Page number (1-based, default 1).
        per_page: Items per page (1-100, default 20).
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        PaginatedDeliveryResponse with delivery records and pagination.

    Raises:
        HTTPException 404: If the store or webhook is not found.
    """
    from app.services import webhook_service as store_webhook_service

    try:
        deliveries, total = await store_webhook_service.get_webhook_deliveries(
            db,
            webhook_id=webhook_id,
            page=page,
            per_page=per_page,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    pages = math.ceil(total / per_page) if total > 0 else 1

    return PaginatedDeliveryResponse(
        items=[WebhookDeliveryResponse.model_validate(d) for d in deliveries],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )
