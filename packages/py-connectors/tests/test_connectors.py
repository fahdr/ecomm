"""
Tests for ecomm_connectors shared package.

For Developers:
    Uses ``respx`` to mock HTTP calls so tests run without real API
    credentials. Each connector is tested independently.

For QA Engineers:
    Tests verify field mapping, pagination, error handling, and the
    factory function. No external services are hit.
"""

import pytest
import httpx
import respx

from ecomm_connectors.base import (
    ConnectorError,
    ConnectionTestResult,
    NormalizedCustomer,
    NormalizedOrder,
    NormalizedProduct,
    PlatformType,
)
from ecomm_connectors.factory import get_connector
from ecomm_connectors.models import StoreConnectionMixin
from ecomm_connectors.schemas import (
    ConnectStoreRequest,
    StoreConnectionResponse,
    TestConnectionResponse,
)
from ecomm_connectors.shopify import ShopifyConnector
from ecomm_connectors.woocommerce import WooCommerceConnector
from ecomm_connectors.platform import PlatformConnector


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------


class TestFactory:
    """Test the get_connector factory function."""

    def test_get_shopify_connector(self):
        """Factory returns ShopifyConnector for shopify type."""
        c = get_connector(PlatformType.shopify, "https://test.myshopify.com", {"access_token": "tok"})
        assert isinstance(c, ShopifyConnector)

    def test_get_woocommerce_connector(self):
        """Factory returns WooCommerceConnector for woocommerce type."""
        c = get_connector(
            PlatformType.woocommerce,
            "https://test.com",
            {"consumer_key": "ck", "consumer_secret": "cs"},
        )
        assert isinstance(c, WooCommerceConnector)

    def test_get_platform_connector(self):
        """Factory returns PlatformConnector for platform type."""
        c = get_connector(PlatformType.platform, "http://localhost:8000", {"api_key": "key"})
        assert isinstance(c, PlatformConnector)

    def test_string_platform_type(self):
        """Factory accepts string platform type."""
        c = get_connector("shopify", "https://test.myshopify.com", {"access_token": "tok"})
        assert isinstance(c, ShopifyConnector)

    def test_unknown_platform_raises(self):
        """Factory raises ConnectorError for unknown platform."""
        with pytest.raises(ConnectorError, match="Unsupported platform"):
            get_connector("magento", "https://test.com", {})


# ---------------------------------------------------------------------------
# Credential validation tests
# ---------------------------------------------------------------------------


class TestCredentialValidation:
    """Test that connectors validate required credentials on init."""

    def test_shopify_missing_token_raises(self):
        """Shopify connector requires access_token."""
        with pytest.raises(ConnectorError, match="access_token"):
            ShopifyConnector("https://test.myshopify.com", {})

    def test_woocommerce_missing_key_raises(self):
        """WooCommerce connector requires consumer_key and consumer_secret."""
        with pytest.raises(ConnectorError, match="consumer_key"):
            WooCommerceConnector("https://test.com", {"consumer_key": "ck"})

    def test_woocommerce_missing_secret_raises(self):
        """WooCommerce connector requires consumer_secret."""
        with pytest.raises(ConnectorError, match="consumer_key"):
            WooCommerceConnector("https://test.com", {})

    def test_platform_missing_api_key_raises(self):
        """Platform connector requires api_key."""
        with pytest.raises(ConnectorError, match="api_key"):
            PlatformConnector("http://localhost:8000", {})


# ---------------------------------------------------------------------------
# Shopify connector tests
# ---------------------------------------------------------------------------


class TestShopifyConnector:
    """Test Shopify connector with mocked HTTP responses."""

    def _connector(self) -> ShopifyConnector:
        """Create a Shopify connector for testing."""
        return ShopifyConnector("https://test.myshopify.com", {"access_token": "test-token"})

    @respx.mock
    @pytest.mark.asyncio
    async def test_connection_success(self):
        """Test connection returns success with shop name."""
        respx.get("https://test.myshopify.com/admin/api/2024-01/shop.json").mock(
            return_value=httpx.Response(200, json={"shop": {"name": "Test Store"}})
        )
        result = await self._connector().test_connection()
        assert result.success is True
        assert result.store_name == "Test Store"
        assert result.platform == "shopify"

    @respx.mock
    @pytest.mark.asyncio
    async def test_connection_failure(self):
        """Test connection returns failure on auth error."""
        respx.get("https://test.myshopify.com/admin/api/2024-01/shop.json").mock(
            return_value=httpx.Response(401, text="Unauthorized")
        )
        result = await self._connector().test_connection()
        assert result.success is False

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_products(self):
        """Fetch products maps Shopify fields to NormalizedProduct."""
        respx.get("https://test.myshopify.com/admin/api/2024-01/products.json").mock(
            return_value=httpx.Response(200, json={
                "products": [
                    {
                        "id": 123,
                        "title": "Widget",
                        "body_html": "<p>A widget</p>",
                        "handle": "widget",
                        "vendor": "Acme",
                        "tags": "sale, new",
                        "variants": [{"price": "19.99", "sku": "WDG-001", "inventory_quantity": 50}],
                        "images": [{"src": "https://cdn.shopify.com/widget.jpg"}],
                    }
                ]
            })
        )
        products, cursor = await self._connector().fetch_products(limit=10)
        assert len(products) == 1
        p = products[0]
        assert isinstance(p, NormalizedProduct)
        assert p.external_id == "123"
        assert p.title == "Widget"
        assert p.price == "19.99"
        assert p.sku == "WDG-001"
        assert p.inventory_quantity == 50
        assert p.vendor == "Acme"
        assert "sale" in p.tags
        assert len(p.images) == 1
        assert cursor is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_products_pagination(self):
        """Link header pagination returns next cursor."""
        next_url = "https://test.myshopify.com/admin/api/2024-01/products.json?page_info=abc"
        respx.get("https://test.myshopify.com/admin/api/2024-01/products.json").mock(
            return_value=httpx.Response(
                200,
                json={"products": [{"id": 1, "title": "P1"}]},
                headers={"link": f'<{next_url}>; rel="next"'},
            )
        )
        products, cursor = await self._connector().fetch_products(limit=1)
        assert len(products) == 1
        assert cursor == next_url

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_orders(self):
        """Fetch orders maps Shopify fields to NormalizedOrder."""
        respx.get("https://test.myshopify.com/admin/api/2024-01/orders.json").mock(
            return_value=httpx.Response(200, json={
                "orders": [
                    {
                        "id": 456,
                        "order_number": 1001,
                        "email": "buyer@test.com",
                        "total_price": "49.99",
                        "currency": "USD",
                        "financial_status": "paid",
                        "created_at": "2025-01-15T10:00:00Z",
                        "line_items": [
                            {"product_id": 123, "title": "Widget", "quantity": 2, "price": "19.99"}
                        ],
                    }
                ]
            })
        )
        orders, cursor = await self._connector().fetch_orders()
        assert len(orders) == 1
        o = orders[0]
        assert isinstance(o, NormalizedOrder)
        assert o.external_id == "456"
        assert o.email == "buyer@test.com"
        assert o.total == "49.99"
        assert o.status == "paid"
        assert len(o.line_items) == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_customers(self):
        """Fetch customers maps Shopify fields to NormalizedCustomer."""
        respx.get("https://test.myshopify.com/admin/api/2024-01/customers.json").mock(
            return_value=httpx.Response(200, json={
                "customers": [
                    {
                        "id": 789,
                        "email": "jane@test.com",
                        "first_name": "Jane",
                        "last_name": "Doe",
                        "orders_count": 5,
                        "total_spent": "250.00",
                        "tags": "vip, returning",
                    }
                ]
            })
        )
        customers, cursor = await self._connector().fetch_customers()
        assert len(customers) == 1
        c = customers[0]
        assert isinstance(c, NormalizedCustomer)
        assert c.email == "jane@test.com"
        assert c.first_name == "Jane"
        assert c.total_orders == 5
        assert "vip" in c.tags

    @respx.mock
    @pytest.mark.asyncio
    async def test_create_product(self):
        """Create product sends correct payload and maps response."""
        respx.post("https://test.myshopify.com/admin/api/2024-01/products.json").mock(
            return_value=httpx.Response(201, json={
                "product": {"id": 999, "title": "New Widget", "variants": [{"price": "29.99"}]}
            })
        )
        product = await self._connector().create_product({"title": "New Widget"})
        assert product.external_id == "999"
        assert product.title == "New Widget"

    @respx.mock
    @pytest.mark.asyncio
    async def test_push_product_update(self):
        """Update product sends correct payload."""
        respx.put("https://test.myshopify.com/admin/api/2024-01/products/123.json").mock(
            return_value=httpx.Response(200, json={
                "product": {"id": 123, "title": "Updated Widget"}
            })
        )
        product = await self._connector().push_product_update("123", {"title": "Updated Widget"})
        assert product.title == "Updated Widget"

    @respx.mock
    @pytest.mark.asyncio
    async def test_rate_limit_retry(self):
        """429 responses trigger retry with Retry-After header."""
        route = respx.get("https://test.myshopify.com/admin/api/2024-01/shop.json")
        route.side_effect = [
            httpx.Response(429, headers={"Retry-After": "0.01"}),
            httpx.Response(200, json={"shop": {"name": "Store"}}),
        ]
        result = await self._connector().test_connection()
        assert result.success is True
        assert route.call_count == 2


# ---------------------------------------------------------------------------
# WooCommerce connector tests
# ---------------------------------------------------------------------------


class TestWooCommerceConnector:
    """Test WooCommerce connector with mocked HTTP responses."""

    def _connector(self) -> WooCommerceConnector:
        """Create a WooCommerce connector for testing."""
        return WooCommerceConnector(
            "https://test.com",
            {"consumer_key": "ck_test", "consumer_secret": "cs_test"},
        )

    @respx.mock
    @pytest.mark.asyncio
    async def test_connection_success(self):
        """Test connection returns success with store name."""
        respx.get("https://test.com/wp-json/wc/v3/system_status").mock(
            return_value=httpx.Response(200, json={
                "environment": {"site_title": "My WooStore"}
            })
        )
        result = await self._connector().test_connection()
        assert result.success is True
        assert result.store_name == "My WooStore"

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_products(self):
        """Fetch products maps WooCommerce fields to NormalizedProduct."""
        respx.get("https://test.com/wp-json/wc/v3/products").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "id": 10,
                        "name": "T-Shirt",
                        "description": "A cool shirt",
                        "price": "24.99",
                        "sku": "TSH-001",
                        "stock_quantity": 100,
                        "permalink": "https://test.com/product/t-shirt",
                        "images": [{"src": "https://test.com/tshirt.jpg"}],
                        "tags": [{"name": "apparel"}, {"name": "summer"}],
                    }
                ],
                headers={"X-WP-TotalPages": "1"},
            )
        )
        products, cursor = await self._connector().fetch_products()
        assert len(products) == 1
        p = products[0]
        assert p.external_id == "10"
        assert p.title == "T-Shirt"
        assert p.price == "24.99"
        assert "apparel" in p.tags
        assert cursor is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_products_pagination(self):
        """WooCommerce pagination uses page numbers."""
        respx.get("https://test.com/wp-json/wc/v3/products").mock(
            return_value=httpx.Response(
                200,
                json=[{"id": 1, "name": "P1"}],
                headers={"X-WP-TotalPages": "3"},
            )
        )
        products, cursor = await self._connector().fetch_products()
        assert cursor == "2"

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_orders(self):
        """Fetch orders maps WooCommerce fields correctly."""
        respx.get("https://test.com/wp-json/wc/v3/orders").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "id": 20,
                        "number": "1002",
                        "billing": {"email": "buyer@woo.com"},
                        "total": "59.99",
                        "currency": "EUR",
                        "status": "completed",
                        "date_created": "2025-02-01T12:00:00",
                        "line_items": [
                            {"product_id": 10, "name": "T-Shirt", "quantity": 2, "total": "49.98"}
                        ],
                    }
                ],
                headers={"X-WP-TotalPages": "1"},
            )
        )
        orders, cursor = await self._connector().fetch_orders()
        assert len(orders) == 1
        o = orders[0]
        assert o.external_id == "20"
        assert o.email == "buyer@woo.com"
        assert o.currency == "EUR"

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_customers(self):
        """Fetch customers maps WooCommerce fields."""
        respx.get("https://test.com/wp-json/wc/v3/customers").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "id": 30,
                        "email": "john@woo.com",
                        "first_name": "John",
                        "last_name": "Smith",
                        "orders_count": 3,
                        "total_spent": "150.00",
                    }
                ],
                headers={"X-WP-TotalPages": "1"},
            )
        )
        customers, cursor = await self._connector().fetch_customers()
        assert len(customers) == 1
        c = customers[0]
        assert c.first_name == "John"
        assert c.total_orders == 3

    @respx.mock
    @pytest.mark.asyncio
    async def test_create_product(self):
        """Create product sends to correct endpoint."""
        respx.post("https://test.com/wp-json/wc/v3/products").mock(
            return_value=httpx.Response(201, json={
                "id": 11, "name": "New Shirt", "price": "19.99"
            })
        )
        product = await self._connector().create_product({"name": "New Shirt"})
        assert product.external_id == "11"

    @respx.mock
    @pytest.mark.asyncio
    async def test_push_product_update(self):
        """Update product sends to correct endpoint."""
        respx.put("https://test.com/wp-json/wc/v3/products/10").mock(
            return_value=httpx.Response(200, json={
                "id": 10, "name": "Updated Shirt"
            })
        )
        product = await self._connector().push_product_update("10", {"name": "Updated Shirt"})
        assert product.title == "Updated Shirt"

    @respx.mock
    @pytest.mark.asyncio
    async def test_api_error_raises(self):
        """HTTP errors raise ConnectorError with status code."""
        respx.get("https://test.com/wp-json/wc/v3/system_status").mock(
            return_value=httpx.Response(403, text="Forbidden")
        )
        result = await self._connector().test_connection()
        assert result.success is False
        assert "403" in result.message


# ---------------------------------------------------------------------------
# Platform connector tests
# ---------------------------------------------------------------------------


class TestPlatformConnector:
    """Test internal platform connector with mocked HTTP responses."""

    def _connector(self) -> PlatformConnector:
        """Create a platform connector for testing."""
        return PlatformConnector("http://localhost:8000", {"api_key": "test-key"})

    @respx.mock
    @pytest.mark.asyncio
    async def test_connection_success(self):
        """Test connection returns success on healthy platform."""
        respx.get("http://localhost:8000/api/v1/health").mock(
            return_value=httpx.Response(200, json={"service": "Dropshipping Platform", "status": "ok"})
        )
        result = await self._connector().test_connection()
        assert result.success is True
        assert result.platform == "platform"

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_products(self):
        """Fetch products from platform's paginated API."""
        respx.get("http://localhost:8000/api/v1/public/products").mock(
            return_value=httpx.Response(200, json={
                "items": [
                    {"id": "abc-123", "title": "Gadget", "price": 39.99, "sku": "GDG-001", "stock": 25}
                ],
                "total": 1,
            })
        )
        products, cursor = await self._connector().fetch_products()
        assert len(products) == 1
        p = products[0]
        assert p.external_id == "abc-123"
        assert p.title == "Gadget"
        assert cursor is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_products_next_page(self):
        """Platform pagination returns next cursor when more pages exist."""
        respx.get("http://localhost:8000/api/v1/public/products").mock(
            return_value=httpx.Response(200, json={
                "items": [{"id": "1", "title": "P1"}],
                "total": 100,
            })
        )
        products, cursor = await self._connector().fetch_products(limit=50)
        assert cursor == "2"

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_orders(self):
        """Fetch orders from platform API."""
        respx.get("http://localhost:8000/api/v1/public/orders").mock(
            return_value=httpx.Response(200, json={
                "items": [
                    {"id": "ord-1", "order_number": "1001", "email": "buyer@platform.com", "total": 79.99, "status": "paid"}
                ],
                "total": 1,
            })
        )
        orders, cursor = await self._connector().fetch_orders()
        assert len(orders) == 1
        assert orders[0].email == "buyer@platform.com"

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_customers(self):
        """Fetch customers from platform API."""
        respx.get("http://localhost:8000/api/v1/public/customers").mock(
            return_value=httpx.Response(200, json={
                "items": [
                    {"id": "cust-1", "email": "alice@platform.com", "first_name": "Alice", "total_orders": 2}
                ],
                "total": 1,
            })
        )
        customers, cursor = await self._connector().fetch_customers()
        assert len(customers) == 1
        assert customers[0].first_name == "Alice"

    @respx.mock
    @pytest.mark.asyncio
    async def test_create_product(self):
        """Create product via platform API."""
        respx.post("http://localhost:8000/api/v1/public/products").mock(
            return_value=httpx.Response(201, json={"id": "new-1", "title": "New Gadget"})
        )
        product = await self._connector().create_product({"title": "New Gadget"})
        assert product.external_id == "new-1"


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestSchemas:
    """Test Pydantic schemas for store connections."""

    def test_connect_store_request_valid(self):
        """Valid request parses correctly."""
        req = ConnectStoreRequest(
            platform=PlatformType.shopify,
            store_url="https://test.myshopify.com",
            credentials={"access_token": "tok"},
        )
        assert req.platform == PlatformType.shopify

    def test_test_connection_response(self):
        """TestConnectionResponse serializes correctly."""
        resp = TestConnectionResponse(success=True, platform="shopify", store_name="Store", message="OK")
        assert resp.success is True


# ---------------------------------------------------------------------------
# Model mixin tests
# ---------------------------------------------------------------------------


class TestModelMixin:
    """Test StoreConnectionMixin columns exist."""

    def test_mixin_has_required_columns(self):
        """Mixin class should define expected mapped columns."""
        assert hasattr(StoreConnectionMixin, "id")
        assert hasattr(StoreConnectionMixin, "user_id")
        assert hasattr(StoreConnectionMixin, "platform")
        assert hasattr(StoreConnectionMixin, "store_url")
        assert hasattr(StoreConnectionMixin, "credentials_encrypted")
        assert hasattr(StoreConnectionMixin, "is_active")
        assert hasattr(StoreConnectionMixin, "last_synced_at")


# ---------------------------------------------------------------------------
# Base class tests
# ---------------------------------------------------------------------------


class TestNormalizedTypes:
    """Test normalized data types."""

    def test_normalized_product_defaults(self):
        """NormalizedProduct should have sensible defaults."""
        p = NormalizedProduct(external_id="1", title="Test")
        assert p.price == "0.00"
        assert p.currency == "USD"
        assert p.images == []
        assert p.tags == []

    def test_normalized_order_defaults(self):
        """NormalizedOrder should have sensible defaults."""
        o = NormalizedOrder(external_id="1")
        assert o.total == "0.00"
        assert o.line_items == []

    def test_normalized_customer_defaults(self):
        """NormalizedCustomer should have sensible defaults."""
        c = NormalizedCustomer(external_id="1")
        assert c.email == ""
        assert c.total_orders == 0

    def test_connector_error_attributes(self):
        """ConnectorError stores status_code and platform."""
        err = ConnectorError("test error", status_code=404, platform="shopify")
        assert str(err) == "test error"
        assert err.status_code == 404
        assert err.platform == "shopify"

    def test_platform_type_enum_values(self):
        """PlatformType enum has expected values."""
        assert PlatformType.shopify.value == "shopify"
        assert PlatformType.woocommerce.value == "woocommerce"
        assert PlatformType.platform.value == "platform"
