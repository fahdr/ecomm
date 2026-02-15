"""
Shopify REST Admin API connector.

For Developers:
    Uses Shopify REST Admin API (2024-01 version) with ``X-Shopify-Access-Token``
    authentication. Implements Link-header pagination and respects the
    leaky-bucket rate limit (40 requests/second burst, 2/s sustained).

    Credentials dict must contain:
        - ``access_token``: Shopify Admin API access token.

For QA Engineers:
    All Shopify responses are mapped to ``NormalizedProduct`` / ``NormalizedOrder``
    / ``NormalizedCustomer`` objects. The ``raw`` field preserves the original
    Shopify JSON for debugging.

For End Users:
    Connect your Shopify store by providing the store URL (e.g.
    ``mystore.myshopify.com``) and your Admin API access token from
    the Shopify Partners dashboard.
"""

from __future__ import annotations

import asyncio
import re
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

# Shopify API version
_API_VERSION = "2024-01"

# Rate limit: wait this long between retries on 429
_RATE_LIMIT_WAIT = 2.0


class ShopifyConnector(AbstractPlatformConnector):
    """
    Connector for Shopify stores via REST Admin API.

    For Developers:
        Instantiate with the store's myshopify.com URL and a credentials
        dict containing ``access_token``. All methods are async.

    Args:
        store_url: Shopify store URL (e.g. "https://mystore.myshopify.com").
        credentials: Dict with ``access_token`` key.
    """

    def __init__(self, store_url: str, credentials: dict[str, str]) -> None:
        super().__init__(store_url, credentials)
        self._access_token = credentials.get("access_token", "")
        if not self._access_token:
            raise ConnectorError(
                "Shopify connector requires 'access_token' in credentials",
                platform="shopify",
            )

    @property
    def _base_api_url(self) -> str:
        """Base URL for Shopify Admin API requests."""
        return f"{self.store_url}/admin/api/{_API_VERSION}"

    def _headers(self) -> dict[str, str]:
        """Standard headers for Shopify API requests."""
        return {
            "X-Shopify-Access-Token": self._access_token,
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        url: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        retries: int = 2,
    ) -> httpx.Response:
        """
        Make an authenticated HTTP request to Shopify with retry on rate limit.

        Args:
            method: HTTP method (GET, POST, PUT).
            url: Full API URL.
            json: Optional JSON body.
            params: Optional query parameters.
            retries: Number of retries on 429 rate limit.

        Returns:
            httpx.Response on success.

        Raises:
            ConnectorError: On non-retryable HTTP errors.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(retries + 1):
                resp = await client.request(
                    method, url, headers=self._headers(), json=json, params=params
                )
                if resp.status_code == 429 and attempt < retries:
                    retry_after = float(resp.headers.get("Retry-After", _RATE_LIMIT_WAIT))
                    await asyncio.sleep(retry_after)
                    continue
                if resp.status_code >= 400:
                    raise ConnectorError(
                        f"Shopify API error {resp.status_code}: {resp.text[:200]}",
                        status_code=resp.status_code,
                        platform="shopify",
                    )
                return resp
        raise ConnectorError("Request failed after retries", platform="shopify")

    @staticmethod
    def _parse_link_header(link_header: str) -> str | None:
        """
        Extract the 'next' page URL from Shopify's Link header.

        Args:
            link_header: Raw Link header value.

        Returns:
            Next page URL or None if no next page.
        """
        if not link_header:
            return None
        for part in link_header.split(","):
            match = re.search(r'<([^>]+)>;\s*rel="next"', part)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _map_product(data: dict[str, Any]) -> NormalizedProduct:
        """
        Map a Shopify product JSON object to NormalizedProduct.

        Args:
            data: Raw Shopify product dict.

        Returns:
            NormalizedProduct with fields mapped from Shopify schema.
        """
        variant = data.get("variants", [{}])[0] if data.get("variants") else {}
        images = [img["src"] for img in data.get("images", []) if img.get("src")]
        tags = [t.strip() for t in data.get("tags", "").split(",") if t.strip()]

        return NormalizedProduct(
            external_id=str(data["id"]),
            title=data.get("title", ""),
            description=data.get("body_html", ""),
            price=str(variant.get("price", "0.00")),
            currency="USD",
            sku=variant.get("sku", ""),
            inventory_quantity=variant.get("inventory_quantity", -1),
            images=images,
            url=f"/products/{data.get('handle', '')}",
            vendor=data.get("vendor", ""),
            tags=tags,
            raw=data,
        )

    @staticmethod
    def _map_order(data: dict[str, Any]) -> NormalizedOrder:
        """
        Map a Shopify order JSON object to NormalizedOrder.

        Args:
            data: Raw Shopify order dict.

        Returns:
            NormalizedOrder with fields mapped from Shopify schema.
        """
        line_items = [
            {
                "product_id": str(li.get("product_id", "")),
                "title": li.get("title", ""),
                "quantity": li.get("quantity", 1),
                "price": str(li.get("price", "0.00")),
            }
            for li in data.get("line_items", [])
        ]
        created_at = None
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        return NormalizedOrder(
            external_id=str(data["id"]),
            order_number=str(data.get("order_number", "")),
            email=data.get("email", ""),
            total=str(data.get("total_price", "0.00")),
            currency=data.get("currency", "USD"),
            status=data.get("financial_status", ""),
            line_items=line_items,
            created_at=created_at,
            raw=data,
        )

    @staticmethod
    def _map_customer(data: dict[str, Any]) -> NormalizedCustomer:
        """
        Map a Shopify customer JSON object to NormalizedCustomer.

        Args:
            data: Raw Shopify customer dict.

        Returns:
            NormalizedCustomer with fields mapped from Shopify schema.
        """
        tags = [t.strip() for t in data.get("tags", "").split(",") if t.strip()]

        return NormalizedCustomer(
            external_id=str(data["id"]),
            email=data.get("email", ""),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            total_orders=data.get("orders_count", 0),
            total_spent=str(data.get("total_spent", "0.00")),
            tags=tags,
            raw=data,
        )

    async def test_connection(self) -> ConnectionTestResult:
        """
        Test the Shopify connection by fetching shop info.

        Returns:
            ConnectionTestResult indicating success or failure.
        """
        try:
            resp = await self._request("GET", f"{self._base_api_url}/shop.json")
            shop = resp.json().get("shop", {})
            return ConnectionTestResult(
                success=True,
                platform="shopify",
                store_name=shop.get("name", ""),
                message=f"Connected to {shop.get('name', 'Shopify store')}",
            )
        except ConnectorError as e:
            return ConnectionTestResult(
                success=False,
                platform="shopify",
                message=str(e),
            )

    async def fetch_products(
        self, *, limit: int = 50, cursor: str | None = None
    ) -> tuple[list[NormalizedProduct], str | None]:
        """
        Fetch products from Shopify using Link-header pagination.

        Args:
            limit: Products per page (max 250 for Shopify).
            cursor: Full URL for the next page (from Link header).

        Returns:
            Tuple of (products, next_page_url).
        """
        if cursor:
            url = cursor
            params = None
        else:
            url = f"{self._base_api_url}/products.json"
            params = {"limit": min(limit, 250)}

        resp = await self._request("GET", url, params=params)
        data = resp.json()
        products = [self._map_product(p) for p in data.get("products", [])]
        next_cursor = self._parse_link_header(resp.headers.get("link", ""))
        return products, next_cursor

    async def fetch_orders(
        self, *, limit: int = 50, cursor: str | None = None
    ) -> tuple[list[NormalizedOrder], str | None]:
        """
        Fetch orders from Shopify using Link-header pagination.

        Args:
            limit: Orders per page (max 250).
            cursor: Full URL for the next page.

        Returns:
            Tuple of (orders, next_page_url).
        """
        if cursor:
            url = cursor
            params = None
        else:
            url = f"{self._base_api_url}/orders.json"
            params = {"limit": min(limit, 250), "status": "any"}

        resp = await self._request("GET", url, params=params)
        data = resp.json()
        orders = [self._map_order(o) for o in data.get("orders", [])]
        next_cursor = self._parse_link_header(resp.headers.get("link", ""))
        return orders, next_cursor

    async def fetch_customers(
        self, *, limit: int = 50, cursor: str | None = None
    ) -> tuple[list[NormalizedCustomer], str | None]:
        """
        Fetch customers from Shopify using Link-header pagination.

        Args:
            limit: Customers per page (max 250).
            cursor: Full URL for the next page.

        Returns:
            Tuple of (customers, next_page_url).
        """
        if cursor:
            url = cursor
            params = None
        else:
            url = f"{self._base_api_url}/customers.json"
            params = {"limit": min(limit, 250)}

        resp = await self._request("GET", url, params=params)
        data = resp.json()
        customers = [self._map_customer(c) for c in data.get("customers", [])]
        next_cursor = self._parse_link_header(resp.headers.get("link", ""))
        return customers, next_cursor

    async def push_product_update(
        self, external_id: str, updates: dict[str, Any]
    ) -> NormalizedProduct:
        """
        Update an existing product on Shopify.

        Args:
            external_id: Shopify product ID.
            updates: Fields to update (title, body_html, variants, etc.).

        Returns:
            Updated NormalizedProduct.
        """
        url = f"{self._base_api_url}/products/{external_id}.json"
        payload = {"product": {"id": int(external_id), **updates}}
        resp = await self._request("PUT", url, json=payload)
        return self._map_product(resp.json()["product"])

    async def create_product(self, product_data: dict[str, Any]) -> NormalizedProduct:
        """
        Create a new product on Shopify.

        Args:
            product_data: Product fields (title, body_html, variants, etc.).

        Returns:
            Created NormalizedProduct.
        """
        url = f"{self._base_api_url}/products.json"
        payload = {"product": product_data}
        resp = await self._request("POST", url, json=payload)
        return self._map_product(resp.json()["product"])
