"""Pydantic schemas for upsell and cross-sell endpoints.

These schemas validate incoming requests and shape outgoing responses for
the ``/api/v1/stores/{store_id}/upsells/*`` routes.

**For Developers:**
    ``CreateUpsellRequest`` and ``UpdateUpsellRequest`` are input schemas.
    ``UpsellResponse`` uses ``from_attributes`` and optionally includes
    the nested ``target_product`` for display. The ``PublicProductResponse``
    import provides the product shape for the storefront.

**For QA Engineers:**
    - ``CreateUpsellRequest.upsell_type`` must be ``"upsell"``,
      ``"cross_sell"``, or ``"bundle"``.
    - ``discount_percentage`` must be 0-100 if provided.
    - ``source_product_id`` and ``target_product_id`` must differ.
    - ``position`` controls display order; defaults to 0.

**For Project Managers:**
    Upsells increase average order value. Store owners link products as
    upsells (upgrade), cross-sells (complementary), or bundles
    (buy-together). An optional discount sweetens the deal.

**For End Users:**
    See recommended products when viewing an item or at checkout.
    Some recommendations may include a special discount.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.public import PublicProductResponse


class CreateUpsellRequest(BaseModel):
    """Schema for creating a new upsell / cross-sell link.

    Attributes:
        source_product_id: UUID of the product that triggers the upsell
            (the product the customer is viewing or buying).
        target_product_id: UUID of the product being recommended.
        upsell_type: Type of recommendation: ``"upsell"``,
            ``"cross_sell"``, or ``"bundle"``.
        discount_percentage: Optional discount offered on the target
            product (0-100).
        title: Optional custom headline for the recommendation.
        description: Optional custom description text.
        position: Display order among other upsells for the source
            product. Defaults to 0.
    """

    source_product_id: uuid.UUID = Field(
        ..., description="Source product UUID"
    )
    target_product_id: uuid.UUID = Field(
        ..., description="Recommended product UUID"
    )
    upsell_type: str = Field(
        ..., description='Type: "upsell", "cross_sell", or "bundle"'
    )
    discount_percentage: Decimal | None = Field(
        None, ge=0, le=100, description="Discount on target product (%)"
    )
    title: str | None = Field(
        None, max_length=255, description="Custom headline"
    )
    description: str | None = Field(
        None, max_length=1000, description="Custom description"
    )
    position: int = Field(
        0, ge=0, description="Display order position"
    )


class UpdateUpsellRequest(BaseModel):
    """Schema for updating an existing upsell (partial update).

    All fields are optional -- only provided fields will be updated.

    Attributes:
        upsell_type: New recommendation type.
        discount_percentage: New discount percentage.
        title: New headline.
        description: New description.
        position: New display order position.
        is_active: Whether the upsell is active.
    """

    upsell_type: str | None = None
    discount_percentage: Decimal | None = Field(None, ge=0, le=100)
    title: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=1000)
    position: int | None = Field(None, ge=0)
    is_active: bool | None = None


class UpsellResponse(BaseModel):
    """Schema for returning upsell data in API responses.

    Attributes:
        id: The upsell link's unique identifier.
        store_id: The parent store's UUID.
        source_product_id: The product that triggers the recommendation.
        target_product_id: The recommended product.
        upsell_type: Type of recommendation (``"upsell"``,
            ``"cross_sell"``, or ``"bundle"``).
        discount_percentage: Discount on the target product (may be null).
        title: Custom headline (may be null).
        description: Custom description (may be null).
        position: Display order position.
        is_active: Whether the upsell is currently active.
        created_at: When the upsell was created.
        target_product: Full target product data for storefront display
            (populated on detail/list endpoints; may be null).
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    store_id: uuid.UUID
    source_product_id: uuid.UUID
    target_product_id: uuid.UUID
    upsell_type: str
    discount_percentage: Decimal | None
    title: str | None
    description: str | None
    position: int
    is_active: bool
    created_at: datetime
    target_product: PublicProductResponse | None = None


class PaginatedUpsellResponse(BaseModel):
    """Schema for paginated upsell list responses.

    Attributes:
        items: List of upsells on this page.
        total: Total number of upsells matching the query.
        page: Current page number (1-based).
        per_page: Number of items per page.
        pages: Total number of pages.
    """

    items: list[UpsellResponse]
    total: int
    page: int
    per_page: int
    pages: int
