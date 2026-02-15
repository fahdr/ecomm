"""
Abstract base class for all ecommerce platform connectors.

For Developers:
    Subclass ``AbstractPlatformConnector`` to add a new platform integration.
    Each method receives credentials at construction time and operates
    asynchronously via httpx.

For QA Engineers:
    All connectors share this interface, making it easy to write
    platform-agnostic integration tests.
"""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class PlatformType(str, enum.Enum):
    """
    Supported ecommerce platform types.

    For End Users:
        These are the platforms you can connect your store from.
    """

    shopify = "shopify"
    woocommerce = "woocommerce"
    platform = "platform"


@dataclass
class NormalizedProduct:
    """
    Platform-agnostic product representation.

    For Developers:
        Connectors map platform-specific fields into this common shape
        so services can work with products regardless of source.

    Attributes:
        external_id: The product ID on the remote platform.
        title: Product title / name.
        description: HTML or plain-text description.
        price: Current price as a string (e.g. "29.99").
        currency: ISO 4217 currency code.
        sku: Stock-keeping unit identifier.
        inventory_quantity: Units in stock (-1 if unknown).
        images: List of image URLs.
        url: Canonical product URL on the remote store.
        vendor: Brand or vendor name.
        tags: List of product tags / categories.
        raw: Original unmodified payload from the platform.
    """

    external_id: str
    title: str
    description: str = ""
    price: str = "0.00"
    currency: str = "USD"
    sku: str = ""
    inventory_quantity: int = -1
    images: list[str] = field(default_factory=list)
    url: str = ""
    vendor: str = ""
    tags: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedOrder:
    """
    Platform-agnostic order representation.

    Attributes:
        external_id: The order ID on the remote platform.
        order_number: Human-readable order number.
        email: Customer email.
        total: Order total as a string.
        currency: ISO 4217 currency code.
        status: Order status (e.g. "paid", "fulfilled").
        line_items: List of dicts with product_id, title, quantity, price.
        created_at: When the order was placed.
        raw: Original unmodified payload.
    """

    external_id: str
    order_number: str = ""
    email: str = ""
    total: str = "0.00"
    currency: str = "USD"
    status: str = ""
    line_items: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedCustomer:
    """
    Platform-agnostic customer representation.

    Attributes:
        external_id: The customer ID on the remote platform.
        email: Customer email address.
        first_name: First name.
        last_name: Last name.
        total_orders: Number of orders placed.
        total_spent: Lifetime spend as a string.
        tags: Customer tags.
        raw: Original unmodified payload.
    """

    external_id: str
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    total_orders: int = 0
    total_spent: str = "0.00"
    tags: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectionTestResult:
    """
    Result of testing a platform connection.

    Attributes:
        success: Whether the connection test passed.
        platform: Platform type string.
        store_name: Name of the connected store (if available).
        message: Human-readable status message.
    """

    success: bool
    platform: str
    store_name: str = ""
    message: str = ""


class AbstractPlatformConnector(ABC):
    """
    Abstract base for ecommerce platform connectors.

    For Developers:
        Implement all abstract methods. Each method should raise
        ``ConnectorError`` on failures rather than raw HTTP exceptions.

    Args:
        store_url: The store's base URL (e.g. "https://mystore.myshopify.com").
        credentials: Platform-specific credential dict.
    """

    def __init__(self, store_url: str, credentials: dict[str, str]) -> None:
        self.store_url = store_url.rstrip("/")
        self.credentials = credentials

    @abstractmethod
    async def test_connection(self) -> ConnectionTestResult:
        """
        Verify the connection to the platform is working.

        Returns:
            ConnectionTestResult with success status and store info.
        """

    @abstractmethod
    async def fetch_products(
        self, *, limit: int = 50, cursor: str | None = None
    ) -> tuple[list[NormalizedProduct], str | None]:
        """
        Fetch a page of products from the platform.

        Args:
            limit: Maximum products per page.
            cursor: Opaque pagination cursor from a previous call.

        Returns:
            Tuple of (products, next_cursor). next_cursor is None when
            there are no more pages.
        """

    @abstractmethod
    async def fetch_orders(
        self, *, limit: int = 50, cursor: str | None = None
    ) -> tuple[list[NormalizedOrder], str | None]:
        """
        Fetch a page of orders from the platform.

        Args:
            limit: Maximum orders per page.
            cursor: Opaque pagination cursor from a previous call.

        Returns:
            Tuple of (orders, next_cursor).
        """

    @abstractmethod
    async def fetch_customers(
        self, *, limit: int = 50, cursor: str | None = None
    ) -> tuple[list[NormalizedCustomer], str | None]:
        """
        Fetch a page of customers from the platform.

        Args:
            limit: Maximum customers per page.
            cursor: Opaque pagination cursor from a previous call.

        Returns:
            Tuple of (customers, next_cursor).
        """

    @abstractmethod
    async def push_product_update(
        self, external_id: str, updates: dict[str, Any]
    ) -> NormalizedProduct:
        """
        Update a product on the remote platform.

        Args:
            external_id: The product's ID on the remote platform.
            updates: Dict of fields to update (title, description, price, etc.).

        Returns:
            The updated product as a NormalizedProduct.

        Raises:
            ConnectorError: If the update fails.
        """

    @abstractmethod
    async def create_product(self, product_data: dict[str, Any]) -> NormalizedProduct:
        """
        Create a new product on the remote platform.

        Args:
            product_data: Dict with product fields (title, description, price, etc.).

        Returns:
            The created product as a NormalizedProduct.

        Raises:
            ConnectorError: If creation fails.
        """


class ConnectorError(Exception):
    """
    Raised when a connector operation fails.

    For Developers:
        Wraps HTTP errors, auth failures, rate limits, etc. into a
        single exception type for consistent error handling.

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code if applicable, else None.
        platform: The platform that raised the error.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        platform: str = "",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.platform = platform
