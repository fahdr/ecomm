"""
Abstract base class for all supplier client integrations.

For Developers:
    Subclass ``BaseSupplierClient`` to add a new supplier integration.
    Every method is async and must normalize responses into the common
    ``SupplierProduct`` / ``ProductSearchResult`` models.

For QA Engineers:
    All supplier clients share this interface, making it straightforward
    to write supplier-agnostic integration tests. ``SupplierError`` is the
    single exception type for all supplier operation failures.

For End Users:
    Supplier clients connect to third-party dropshipping suppliers
    (AliExpress, CJDropship, etc.) to import products into your store.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ecomm_suppliers.models import ProductSearchResult, SupplierProduct


class SupplierError(Exception):
    """
    Raised when a supplier client operation fails.

    For Developers:
        Wraps HTTP errors, auth failures, rate limits, parse errors, etc.
        into a single exception type for consistent error handling across
        all supplier integrations.

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code if the error originated from an HTTP call, else None.
        supplier: The supplier platform that raised the error (e.g. "aliexpress").
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        supplier: str = "",
    ) -> None:
        """
        Initialize a SupplierError.

        Args:
            message: Human-readable error description.
            status_code: HTTP status code if applicable, else None.
            supplier: Supplier platform identifier (e.g. "aliexpress", "cjdropship").
        """
        super().__init__(message)
        self.status_code = status_code
        self.supplier = supplier


class BaseSupplierClient(ABC):
    """
    Abstract base class for all supplier client integrations.

    For Developers:
        Implement all abstract methods in your supplier subclass. Each
        method should raise ``SupplierError`` on failures rather than raw
        HTTP or parsing exceptions. Call ``await close()`` when done to
        release resources.

    For QA Engineers:
        Mock this class to test service code without hitting real supplier
        APIs. All methods return the shared model types from
        ``ecomm_suppliers.models``.

    Args:
        api_key: Optional API key for authenticated supplier access.
            When None, the client should fall back to demo/mock data.
    """

    def __init__(self, api_key: str | None = None) -> None:
        """
        Initialize the supplier client.

        Args:
            api_key: Optional API key for the supplier platform.
                If not provided, the client operates in demo mode with mock data.
        """
        self._api_key = api_key

    @property
    def is_demo_mode(self) -> bool:
        """
        Whether the client is running in demo mode (no real API key).

        Returns:
            True if no API key was provided and mock data will be used.
        """
        return self._api_key is None

    @abstractmethod
    async def search_products(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20,
    ) -> ProductSearchResult:
        """
        Search for products on the supplier platform.

        Args:
            query: Search query string (e.g. "wireless earbuds", "yoga mat").
            page: Page number for pagination (1-indexed).
            page_size: Number of results per page (default 20, max varies by supplier).

        Returns:
            ProductSearchResult containing matching products and pagination info.

        Raises:
            SupplierError: If the search request fails.
        """

    @abstractmethod
    async def get_product(self, product_id: str) -> SupplierProduct:
        """
        Fetch a single product by its supplier platform ID.

        Args:
            product_id: The product's ID on the supplier platform.

        Returns:
            SupplierProduct with full product details, variants, and images.

        Raises:
            SupplierError: If the product is not found or the request fails.
        """

    @abstractmethod
    async def get_product_by_url(self, url: str) -> SupplierProduct:
        """
        Fetch a product by its URL on the supplier platform.

        For End Users:
            Paste a product link from the supplier website and the system
            will automatically import the product details.

        Args:
            url: Full URL to the product page on the supplier website.

        Returns:
            SupplierProduct with full product details, variants, and images.

        Raises:
            SupplierError: If the URL cannot be parsed or the product is not found.
        """

    async def close(self) -> None:
        """
        Clean up resources (HTTP clients, connections, etc.).

        For Developers:
            Override this method if your client holds persistent resources
            (e.g. an httpx.AsyncClient). The default implementation is a no-op.
        """
        pass

    async def __aenter__(self) -> BaseSupplierClient:
        """Support async context manager usage."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        """Close resources on context manager exit."""
        await self.close()
