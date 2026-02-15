"""
Supplier integrations for the ecomm dropshipping platform.

For Developers:
    This package provides a unified interface for integrating with
    third-party dropshipping suppliers (AliExpress, CJDropship, etc.).
    Use ``SupplierFactory.create()`` to get a client, or import specific
    clients directly.

    Quick start::

        from ecomm_suppliers import SupplierFactory

        async with SupplierFactory.create("aliexpress") as client:
            results = await client.search_products("wireless earbuds")
            for product in results.products:
                print(f"{product.title}: ${product.price}")

For QA Engineers:
    All supplier clients share the ``BaseSupplierClient`` interface.
    In demo mode (no API key), clients return deterministic mock data
    suitable for automated testing.

For End Users:
    Import products from global suppliers into your store with automatic
    pricing, image optimization, and variant management.
"""

__version__ = "0.1.0"

from ecomm_suppliers.aliexpress import AliExpressClient
from ecomm_suppliers.base import BaseSupplierClient, SupplierError
from ecomm_suppliers.cjdropship import CJDropshipClient
from ecomm_suppliers.factory import SupplierFactory
from ecomm_suppliers.image_service import ImageService
from ecomm_suppliers.models import (
    ProductSearchResult,
    ShippingInfo,
    SupplierProduct,
    SupplierRating,
    SupplierVariant,
)
from ecomm_suppliers.normalizer import ProductNormalizer

__all__ = [
    # Factory
    "SupplierFactory",
    # Base
    "BaseSupplierClient",
    "SupplierError",
    # Clients
    "AliExpressClient",
    "CJDropshipClient",
    # Models
    "SupplierProduct",
    "SupplierVariant",
    "ShippingInfo",
    "SupplierRating",
    "ProductSearchResult",
    # Utilities
    "ProductNormalizer",
    "ImageService",
]
