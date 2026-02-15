"""Pydantic schemas for supplier management endpoints.

These schemas validate incoming requests and shape outgoing responses for
the ``/api/v1/stores/{store_id}/suppliers/*`` routes and the product-supplier
linking sub-routes.

**For Developers:**
    ``CreateSupplierRequest`` and ``UpdateSupplierRequest`` are input schemas.
    ``SupplierResponse`` uses ``from_attributes`` to serialize ORM instances.
    ``LinkProductSupplierRequest`` and ``ProductSupplierResponse`` handle
    many-to-many product-supplier relationships.

**For QA Engineers:**
    - ``CreateSupplierRequest.name`` is required, 1-255 characters.
    - ``LinkProductSupplierRequest.supplier_cost`` must be >= 0.
    - ``SupplierResponse.reliability_score`` is a float 0.0-100.0.
    - Only one product-supplier link should be ``is_primary`` per product.

**For Project Managers:**
    Supplier management is core to the dropshipping model. Merchants
    track supplier contact info, reliability, and shipping times.
    Each product links to one or more suppliers with cost data for
    profit calculations.

**For End Users:**
    Store owners manage their supplier relationships through the
    dashboard, linking products to suppliers and tracking costs.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


class CreateSupplierRequest(BaseModel):
    """Schema for creating a new supplier record.

    Attributes:
        name: Supplier company or brand name (1-255 characters).
        website: Optional supplier website URL.
        contact_email: Optional primary contact email address.
        contact_phone: Optional primary contact phone number.
        notes: Optional free-form notes about this supplier.
    """

    name: str = Field(
        ..., min_length=1, max_length=255, description="Supplier name"
    )
    website: str | None = Field(
        None, max_length=2048, description="Supplier website URL"
    )
    contact_email: EmailStr | None = Field(
        None, description="Primary contact email"
    )
    contact_phone: str | None = Field(
        None, max_length=50, description="Primary contact phone"
    )
    notes: str | None = Field(
        None, max_length=2000, description="Internal notes"
    )


class UpdateSupplierRequest(BaseModel):
    """Schema for updating an existing supplier (partial update).

    All fields are optional -- only provided fields will be updated.

    Attributes:
        name: New supplier name (1-255 characters).
        website: New website URL.
        contact_email: New contact email.
        contact_phone: New contact phone.
        notes: New internal notes.
        status: New status (``"active"`` or ``"inactive"``).
    """

    name: str | None = Field(None, min_length=1, max_length=255)
    website: str | None = Field(None, max_length=2048)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(None, max_length=50)
    notes: str | None = Field(None, max_length=2000)
    status: str | None = None


class SupplierResponse(BaseModel):
    """Schema for returning supplier data in API responses.

    Attributes:
        id: The supplier's unique identifier.
        store_id: The parent store's UUID.
        name: Supplier company or brand name.
        website: Supplier website URL (may be null).
        contact_email: Primary contact email (may be null).
        contact_phone: Primary contact phone (may be null).
        notes: Internal notes (may be null).
        status: Current status (``"active"`` or ``"inactive"``).
        avg_shipping_days: Average shipping time in days (may be null
            if no fulfilled orders yet).
        reliability_score: Computed reliability score 0.0-100.0 (may be
            null if insufficient data).
        created_at: When the supplier record was created.
        updated_at: When the supplier record was last modified.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    store_id: uuid.UUID
    name: str
    website: str | None
    contact_email: str | None
    contact_phone: str | None
    notes: str | None
    status: str
    avg_shipping_days: float | None
    reliability_score: float | None
    created_at: datetime
    updated_at: datetime


class PaginatedSupplierResponse(BaseModel):
    """Schema for paginated supplier list responses.

    Attributes:
        items: List of suppliers on this page.
        total: Total number of suppliers matching the query.
        page: Current page number (1-based).
        per_page: Number of items per page.
        pages: Total number of pages.
    """

    items: list[SupplierResponse]
    total: int
    page: int
    per_page: int
    pages: int


class LinkProductSupplierRequest(BaseModel):
    """Schema for linking a product to a supplier.

    Attributes:
        supplier_id: UUID of the supplier to link.
        supplier_url: Optional URL to the product on the supplier's site.
        supplier_sku: Optional supplier-side SKU for the product.
        supplier_cost: The cost charged by the supplier for this product.
        is_primary: Whether this is the primary (default) supplier for
            the product. Only one link per product should be primary.
    """

    supplier_id: uuid.UUID = Field(..., description="Supplier UUID")
    supplier_url: str | None = Field(
        None, max_length=2048, description="Supplier product URL"
    )
    supplier_sku: str | None = Field(
        None, max_length=100, description="Supplier SKU"
    )
    supplier_cost: Decimal = Field(
        ..., ge=0, description="Supplier cost per unit"
    )
    is_primary: bool = Field(
        False, description="Is this the primary supplier for the product?"
    )


class ProductSupplierResponse(BaseModel):
    """Schema for returning a product-supplier link in API responses.

    Attributes:
        id: The link record's unique identifier.
        product_id: The linked product's UUID.
        supplier_id: The linked supplier's UUID.
        supplier_url: URL to the product on the supplier's site (may be null).
        supplier_sku: Supplier-side SKU (may be null).
        supplier_cost: Cost charged by the supplier.
        is_primary: Whether this is the primary supplier for the product.
        supplier_name: Denormalised supplier name for display convenience
            (may be null if not joined).
        created_at: When the link was created.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    product_id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_url: str | None
    supplier_sku: str | None
    supplier_cost: Decimal
    is_primary: bool
    supplier_name: str | None = None
    created_at: datetime
