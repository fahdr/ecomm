"""Pydantic schemas for bulk operation endpoints (Feature 26).

These schemas validate incoming requests and shape outgoing responses for
the ``/api/v1/stores/{store_id}/bulk/*`` routes.

**For Developers:**
    ``BulkProductUpdateRequest`` and ``BulkProductDeleteRequest`` are input
    schemas for batch operations. ``BulkOperationResponse`` reports success
    and failure counts. ``BulkPriceUpdateRequest`` handles batch price
    adjustments.

**For QA Engineers:**
    - ``BulkProductUpdateRequest.product_ids`` must have at least 1 item.
    - ``BulkProductUpdateRequest.updates`` is a partial product dict
      (same fields as ``UpdateProductRequest``).
    - ``BulkPriceUpdateRequest.adjustment_type`` is ``"percentage"`` or
      ``"fixed"``.
    - ``BulkOperationResponse.errors`` contains per-item failure details.
    - ``succeeded + failed`` should always equal ``total``.

**For Project Managers:**
    Bulk operations save time for stores with large catalogues. Merchants
    can update prices, statuses, or delete products in batch instead of
    one at a time.

**For End Users:**
    Select multiple products on the dashboard and apply changes in bulk:
    update prices, change status, or delete products all at once.
"""

import uuid
from decimal import Decimal

from pydantic import BaseModel, Field


class BulkProductUpdateRequest(BaseModel):
    """Schema for updating multiple products at once.

    Attributes:
        product_ids: List of product UUIDs to update.
        updates: Dictionary of fields to update. Uses the same field
            names as ``UpdateProductRequest`` (e.g.
            ``{"status": "active", "price": "29.99"}``).
    """

    product_ids: list[uuid.UUID] = Field(
        ..., min_length=1, description="Product UUIDs to update"
    )
    updates: dict = Field(
        ..., description="Partial product fields to apply"
    )


class BulkProductDeleteRequest(BaseModel):
    """Schema for deleting multiple products at once.

    Attributes:
        product_ids: List of product UUIDs to delete.
    """

    product_ids: list[uuid.UUID] = Field(
        ..., min_length=1, description="Product UUIDs to delete"
    )


class BulkOperationResponse(BaseModel):
    """Schema for the result of a bulk operation.

    Attributes:
        total: Total number of items in the batch.
        succeeded: Number of items that were successfully processed.
        failed: Number of items that failed.
        errors: Optional list of per-item error details. Each entry
            contains ``product_id`` and ``error`` keys.
    """

    total: int
    succeeded: int
    failed: int
    errors: list[dict] | None = None


class BulkPriceUpdateRequest(BaseModel):
    """Schema for adjusting prices on multiple products at once.

    Attributes:
        product_ids: List of product UUIDs to adjust.
        adjustment_type: Type of price adjustment:
            ``"percentage"`` (e.g. +10% or -10%) or
            ``"fixed"`` (e.g. +$5.00 or -$5.00).
        adjustment_value: The adjustment amount. Positive values
            increase prices; negative values decrease them. For
            percentage adjustments, this is a percentage (e.g.
            ``10`` for +10%, ``-15`` for -15%).
    """

    product_ids: list[uuid.UUID] = Field(
        ..., min_length=1, description="Product UUIDs to adjust"
    )
    adjustment_type: str = Field(
        ..., description='Adjustment type: "percentage" or "fixed"'
    )
    adjustment_value: Decimal = Field(
        ..., description="Adjustment amount (positive to increase, negative to decrease)"
    )
