"""
Pydantic schemas for request/response validation.

Re-exports all schema modules for convenient access.
"""

from app.schemas.imports import (
    ImportJobCreate,
    ImportJobResponse,
    ImportJobList,
    BulkImportCreate,
    ImportPreviewRequest,
    ImportPreviewResponse,
)
from app.schemas.suppliers import (
    SupplierAccountCreate,
    SupplierAccountUpdate,
    SupplierAccountResponse,
    SupplierAccountListResponse,
)
from app.schemas.products import (
    ProductSearchRequest,
    ProductSearchResponse,
    ProductPreview,
)
from app.schemas.connections import (
    StoreConnectionCreate,
    StoreConnectionUpdate,
    StoreConnectionResponse,
    StoreConnectionListResponse,
)
from app.schemas.price_watch import (
    PriceWatchCreate,
    PriceWatchResponse,
    PriceWatchList,
)

__all__ = [
    "ImportJobCreate",
    "ImportJobResponse",
    "ImportJobList",
    "BulkImportCreate",
    "ImportPreviewRequest",
    "ImportPreviewResponse",
    "SupplierAccountCreate",
    "SupplierAccountUpdate",
    "SupplierAccountResponse",
    "SupplierAccountListResponse",
    "ProductSearchRequest",
    "ProductSearchResponse",
    "ProductPreview",
    "StoreConnectionCreate",
    "StoreConnectionUpdate",
    "StoreConnectionResponse",
    "StoreConnectionListResponse",
    "PriceWatchCreate",
    "PriceWatchResponse",
    "PriceWatchList",
]
