"""
WooCommerce REST API v3 connector.

For Developers:
    Uses WooCommerce REST API v3 with HMAC-SHA256 (consumer key/secret)
    authentication. Pagination is offset-based (``page`` + ``per_page``
    query params).

    Credentials dict must contain:
        - ``consumer_key``: WooCommerce REST API consumer key.
        - ``consumer_secret``: WooCommerce REST API consumer secret.

For QA Engineers:
    Responses map to the same ``NormalizedProduct`` / ``NormalizedOrder``
    / ``NormalizedCustomer`` as Shopify, so tests can be platform-agnostic.

For End Users:
    Connect your WooCommerce store by providing the store URL and
    your REST API consumer key + secret from WooCommerce Settings > REST API.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from ecomm_connectors.base import (
    AbstractPlatformConnector,
    ConnectionTestResult,
    ConnectorError,
    NormalizedCustomer,
    NormalizedOrder,
    NormalizedProduct,
)


class WooCommerceConnector(AbstractPlatformConnector):
    """
    Connector for WooCommerce stores via REST API v3.

    For Developers:
        Instantiate with the store URL and credentials dict containing
        ``consumer_key`` and ``consumer_secret``.

    Args:
        store_url: WooCommerce store URL (e.g. "https://mystore.com").
        credentials: Dict with ``consumer_key`` and ``consumer_secret``.
    """

    def __init__(self, store_url: str, credentials: dict[str, str]) -> None:
        super().__init__(store_url, credentials)
        self._consumer_key = credentials.get("consumer_key", "")
        self._consumer_secret = credentials.get("consumer_secret", "")
        if not self._consumer_key or not self._consumer_secret:
            raise ConnectorError(
                "WooCommerce connector requires 'consumer_key' and 'consumer_secret'",
                platform="woocommerce",
            )

    @property
    def _base_api_url(self) -> str:
        """Base URL for WooCommerce REST API v3."""
        return f"{self.store_url}/wp-json/wc/v3"

    def _auth_params(self) -> dict[str, str]:
        """Query-string auth params for WooCommerce API."""
        return {
            "consumer_key": self._consumer_key,
            "consumer_secret": self._consumer_secret,
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
    ) -> httpx.Response:
        """
        Make an authenticated request to the WooCommerce API.

        Args:
            method: HTTP method.
            endpoint: API path relative to base URL (e.g. "/products").
            json: Optional JSON body.
            params: Optional query parameters (merged with auth).

        Returns:
            httpx.Response on success.

        Raises:
            ConnectorError: On HTTP errors.
        """
        url = f"{self._base_api_url}{endpoint}"
        merged_params = {**self._auth_params(), **(params or {})}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                method, url, headers={"Content-Type": "application/json"},
                json=json, params=merged_params,
            )
            if resp.status_code >= 400:
                raise ConnectorError(
                    f"WooCommerce API error {resp.status_code}: {resp.text[:200]}",
                    status_code=resp.status_code,
                    platform="woocommerce",
                )
            return resp

    @staticmethod
    def _map_product(data: dict[str, Any]) -> NormalizedProduct:
        """
        Map a WooCommerce product object to NormalizedProduct.

        Args:
            data: Raw WooCommerce product dict.

        Returns:
            NormalizedProduct.
        """
        images = [img["src"] for img in data.get("images", []) if img.get("src")]
        tags = [t["name"] for t in data.get("tags", []) if t.get("name")]

        return NormalizedProduct(
            external_id=str(data["id"]),
            title=data.get("name", ""),
            description=data.get("description", ""),
            price=data.get("price", "0.00"),
            currency="USD",
            sku=data.get("sku", ""),
            inventory_quantity=data.get("stock_quantity") or -1,
            images=images,
            url=data.get("permalink", ""),
            vendor="",
            tags=tags,
            raw=data,
        )

    @staticmethod
    def _map_order(data: dict[str, Any]) -> NormalizedOrder:
        """
        Map a WooCommerce order object to NormalizedOrder.

        Args:
            data: Raw WooCommerce order dict.

        Returns:
            NormalizedOrder.
        """
        line_items = [
            {
                "product_id": str(li.get("product_id", "")),
                "title": li.get("name", ""),
                "quantity": li.get("quantity", 1),
                "price": str(li.get("total", "0.00")),
            }
            for li in data.get("line_items", [])
        ]
        created_at = None
        if data.get("date_created"):
            try:
                created_at = datetime.fromisoformat(data["date_created"]).replace(
                    tzinfo=timezone.utc
                )
            except (ValueError, AttributeError):
                pass

        billing = data.get("billing", {})

        return NormalizedOrder(
            external_id=str(data["id"]),
            order_number=str(data.get("number", "")),
            email=billing.get("email", ""),
            total=data.get("total", "0.00"),
            currency=data.get("currency", "USD"),
            status=data.get("status", ""),
            line_items=line_items,
            created_at=created_at,
            raw=data,
        )

    @staticmethod
    def _map_customer(data: dict[str, Any]) -> NormalizedCustomer:
        """
        Map a WooCommerce customer object to NormalizedCustomer.

        Args:
            data: Raw WooCommerce customer dict.

        Returns:
            NormalizedCustomer.
        """
        return NormalizedCustomer(
            external_id=str(data["id"]),
            email=data.get("email", ""),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            total_orders=data.get("orders_count", 0),
            total_spent=str(data.get("total_spent", "0.00")),
            tags=[],
            raw=data,
        )

    async def test_connection(self) -> ConnectionTestResult:
        """
        Test the WooCommerce connection by fetching system status.

        Returns:
            ConnectionTestResult with store info.
        """
        try:
            resp = await self._request("GET", "/system_status")
            env = resp.json().get("environment", {})
            store_name = env.get("site_title", "WooCommerce Store")
            return ConnectionTestResult(
                success=True,
                platform="woocommerce",
                store_name=store_name,
                message=f"Connected to {store_name}",
            )
        except ConnectorError as e:
            return ConnectionTestResult(
                success=False,
                platform="woocommerce",
                message=str(e),
            )

    async def fetch_products(
        self, *, limit: int = 50, cursor: str | None = None
    ) -> tuple[list[NormalizedProduct], str | None]:
        """
        Fetch products from WooCommerce with offset pagination.

        Args:
            limit: Products per page (max 100 for WooCommerce).
            cursor: Page number as string (e.g. "2"). None means page 1.

        Returns:
            Tuple of (products, next_page_str_or_none).
        """
        page = int(cursor) if cursor else 1
        per_page = min(limit, 100)

        resp = await self._request(
            "GET", "/products", params={"page": str(page), "per_page": str(per_page)}
        )
        data = resp.json()
        products = [self._map_product(p) for p in data]

        total_pages = int(resp.headers.get("X-WP-TotalPages", "1"))
        next_cursor = str(page + 1) if page < total_pages else None
        return products, next_cursor

    async def fetch_orders(
        self, *, limit: int = 50, cursor: str | None = None
    ) -> tuple[list[NormalizedOrder], str | None]:
        """
        Fetch orders from WooCommerce with offset pagination.

        Args:
            limit: Orders per page (max 100).
            cursor: Page number as string.

        Returns:
            Tuple of (orders, next_page_str_or_none).
        """
        page = int(cursor) if cursor else 1
        per_page = min(limit, 100)

        resp = await self._request(
            "GET", "/orders", params={"page": str(page), "per_page": str(per_page)}
        )
        data = resp.json()
        orders = [self._map_order(o) for o in data]

        total_pages = int(resp.headers.get("X-WP-TotalPages", "1"))
        next_cursor = str(page + 1) if page < total_pages else None
        return orders, next_cursor

    async def fetch_customers(
        self, *, limit: int = 50, cursor: str | None = None
    ) -> tuple[list[NormalizedCustomer], str | None]:
        """
        Fetch customers from WooCommerce with offset pagination.

        Args:
            limit: Customers per page (max 100).
            cursor: Page number as string.

        Returns:
            Tuple of (customers, next_page_str_or_none).
        """
        page = int(cursor) if cursor else 1
        per_page = min(limit, 100)

        resp = await self._request(
            "GET", "/customers", params={"page": str(page), "per_page": str(per_page)}
        )
        data = resp.json()
        customers = [self._map_customer(c) for c in data]

        total_pages = int(resp.headers.get("X-WP-TotalPages", "1"))
        next_cursor = str(page + 1) if page < total_pages else None
        return customers, next_cursor

    async def push_product_update(
        self, external_id: str, updates: dict[str, Any]
    ) -> NormalizedProduct:
        """
        Update a product on WooCommerce.

        Args:
            external_id: WooCommerce product ID.
            updates: Fields to update (name, description, regular_price, etc.).

        Returns:
            Updated NormalizedProduct.
        """
        resp = await self._request("PUT", f"/products/{external_id}", json=updates)
        return self._map_product(resp.json())

    async def create_product(self, product_data: dict[str, Any]) -> NormalizedProduct:
        """
        Create a new product on WooCommerce.

        Args:
            product_data: Product fields (name, description, regular_price, etc.).

        Returns:
            Created NormalizedProduct.
        """
        resp = await self._request("POST", "/products", json=product_data)
        return self._map_product(resp.json())
