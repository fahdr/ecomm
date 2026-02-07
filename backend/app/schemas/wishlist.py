"""Pydantic schemas for wishlist endpoints.

These schemas validate incoming requests and shape outgoing responses for
the customer wishlist feature.

**For Developers:**
    ``WishlistItemResponse`` nests the full public product data so the
    storefront can display wishlist items without additional API calls.

**For QA Engineers:**
    - ``WishlistAddRequest`` requires a valid product UUID.
    - Duplicate wishlist entries return 409 Conflict.
    - Products from other stores cannot be wishlisted (404).

**For End Users:**
    Save products to your wishlist and view them later from your account.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.public import PublicProductResponse


class WishlistAddRequest(BaseModel):
    """Schema for adding a product to the wishlist.

    Attributes:
        product_id: UUID of the product to wishlist.
    """

    product_id: uuid.UUID


class WishlistItemResponse(BaseModel):
    """Schema for returning a wishlist item with nested product data.

    Attributes:
        id: Wishlist item UUID.
        customer_id: Customer UUID.
        product_id: Product UUID.
        created_at: When the item was added.
        product: Full public product data.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    customer_id: uuid.UUID
    product_id: uuid.UUID
    created_at: datetime
    product: PublicProductResponse


class PaginatedWishlistResponse(BaseModel):
    """Schema for paginated wishlist list responses.

    Attributes:
        items: List of wishlist items on this page.
        total: Total number of items in the wishlist.
        page: Current page number (1-based).
        per_page: Number of items per page.
        pages: Total number of pages.
    """

    items: list[WishlistItemResponse]
    total: int
    page: int
    per_page: int
    pages: int
