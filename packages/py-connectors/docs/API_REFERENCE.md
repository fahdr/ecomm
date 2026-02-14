# API Reference

> Part of [ecomm_connectors](README.md) documentation

Complete API documentation for all exported classes, functions, and types in `ecomm_connectors`.

## Factory Function

### `get_connector(platform, store_url, credentials)`

Instantiate the correct connector for a given platform type.

**Parameters:**
- `platform` (PlatformType | str): Platform identifier (enum or string: "shopify", "woocommerce", "platform")
- `store_url` (str): The remote store's base URL
- `credentials` (dict[str, str]): Platform-specific credentials dict

**Returns:**
- `AbstractPlatformConnector`: Initialized connector instance

**Raises:**
- `ConnectorError`: If platform type is not supported

**Example:**
```python
from ecomm_connectors.factory import get_connector
from ecomm_connectors.base import PlatformType

connector = get_connector(
    PlatformType.shopify,
    "https://mystore.myshopify.com",
    {"access_token": "shpat_xxxx"}
)
```

## Abstract Base Class

### `AbstractPlatformConnector`

Base class for all platform connectors. Do not instantiate directly — use `get_connector()` or a concrete subclass.

**Constructor:**
```python
AbstractPlatformConnector(store_url: str, credentials: dict[str, str])
```

**Attributes:**
- `store_url` (str): Store base URL (trailing slash removed)
- `credentials` (dict[str, str]): Platform-specific credentials

**Abstract Methods:**

#### Methods

All methods are async and return normalized data types or raise `ConnectorError` on failure.

**`test_connection() -> ConnectionTestResult`**
Verify connection by making a lightweight API call. Returns object with `success`, `platform`, `store_name`, `message`.

**`fetch_products(limit=50, cursor=None) -> tuple[list[NormalizedProduct], str | None]`**
Fetch products. Returns (products, next_cursor). cursor=None means no more pages.

**`fetch_orders(limit=50, cursor=None) -> tuple[list[NormalizedOrder], str | None]`**
Fetch orders with pagination.

**`fetch_customers(limit=50, cursor=None) -> tuple[list[NormalizedCustomer], str | None]`**
Fetch customers with pagination.

**`push_product_update(external_id, updates) -> NormalizedProduct`**
Update existing product. Raises `ConnectorError` on failure.

**`create_product(product_data) -> NormalizedProduct`**
Create new product. Raises `ConnectorError` on failure.

## Concrete Connectors

### `ShopifyConnector`

Shopify REST Admin API v2024-01 connector.

**Constructor:**
```python
ShopifyConnector(store_url: str, credentials: dict[str, str])
```

**Required Credentials:**
- `access_token` (str): Shopify Admin API access token

**Pagination:**
- Uses Link header (`rel="next"`)
- Max 250 items per page

**Rate Limiting:**
- Retries on 429 with `Retry-After` header (default 2.0s wait)

**Example:**
```python
connector = ShopifyConnector(
    "https://mystore.myshopify.com",
    {"access_token": "shpat_xxxx"}
)
```

### `WooCommerceConnector`

WooCommerce REST API v3 connector.

**Constructor:**
```python
WooCommerceConnector(store_url: str, credentials: dict[str, str])
```

**Required Credentials:**
- `consumer_key` (str): WooCommerce REST API consumer key
- `consumer_secret` (str): WooCommerce REST API consumer secret

**Pagination:**
- Uses page numbers (cursor is page number as string)
- Max 100 items per page
- Reads `X-WP-TotalPages` header

**Example:**
```python
connector = WooCommerceConnector(
    "https://mystore.com",
    {"consumer_key": "ck_xxxx", "consumer_secret": "cs_xxxx"}
)
```

### `PlatformConnector`

Internal dropshipping platform connector.

**Constructor:**
```python
PlatformConnector(store_url: str, credentials: dict[str, str])
```

**Required Credentials:**
- `api_key` (str): Platform API key

**Pagination:**
- Uses page numbers (cursor is page number as string)
- Reads `{"items": [...], "total": N}` response format

**Example:**
```python
connector = PlatformConnector(
    "http://localhost:8000",
    {"api_key": "platform-key"}
)
```

## Data Types

### `PlatformType` (Enum)

Supported e-commerce platform types.

**Values:**
- `PlatformType.shopify` = "shopify"
- `PlatformType.woocommerce` = "woocommerce"
- `PlatformType.platform` = "platform"

### `NormalizedProduct` (Dataclass)

**Fields:** `external_id` (str), `title` (str), `description` (str, default ""), `price` (str, default "0.00"), `currency` (str, default "USD"), `sku` (str, default ""), `inventory_quantity` (int, default -1), `images` (list[str], default []), `url` (str, default ""), `vendor` (str, default ""), `tags` (list[str], default []), `raw` (dict, default {})

### `NormalizedOrder` (Dataclass)

**Fields:** `external_id` (str), `order_number` (str, default ""), `email` (str, default ""), `total` (str, default "0.00"), `currency` (str, default "USD"), `status` (str, default ""), `line_items` (list[dict], default []), `created_at` (datetime | None, default None), `raw` (dict, default {})

### `NormalizedCustomer` (Dataclass)

**Fields:** `external_id` (str), `email` (str, default ""), `first_name` (str, default ""), `last_name` (str, default ""), `total_orders` (int, default 0), `total_spent` (str, default "0.00"), `tags` (list[str], default []), `raw` (dict, default {})

### `ConnectionTestResult` (Dataclass)

Result of testing a platform connection.

**Fields:**
- `success` (bool): Whether the test passed
- `platform` (str): Platform type string
- `store_name` (str): Name of connected store (default "")
- `message` (str): Human-readable status message (default "")

### `ConnectorError` (Exception)

Exception raised when a connector operation fails.

**Constructor:**
```python
ConnectorError(message: str, *, status_code: int | None = None, platform: str = "")
```

**Attributes:**
- `status_code` (int | None): HTTP status code if applicable
- `platform` (str): Platform that raised the error

**Example:**
```python
try:
    await connector.fetch_products()
except ConnectorError as e:
    print(f"{e.platform} error {e.status_code}: {e}")
```

## Pydantic Schemas

### Pydantic Schemas

**`ConnectStoreRequest`**: `platform` (PlatformType), `store_url` (str), `credentials` (dict), `store_name` (str, default "")

**`StoreConnectionResponse`**: `id` (str), `platform` (PlatformType), `store_url` (str), `store_name` (str), `is_active` (bool), `last_synced_at` (datetime | None), `created_at` (datetime). Config: `from_attributes = True`

**`TestConnectionResponse`**: `success` (bool), `platform` (str), `store_name` (str, default ""), `message` (str, default "")

**`SyncStatusResponse`**: `connection_id` (str), `products_synced` (int, default 0), `orders_synced` (int, default 0), `customers_synced` (int, default 0), `last_synced_at` (datetime | None, default None), `status` (str, default "pending")

## SQLAlchemy Model

### `StoreConnectionMixin`

Mixin providing store connection columns for SQLAlchemy models.

**Usage:**
```python
from ecomm_core.models.base import Base
from ecomm_connectors.models import StoreConnectionMixin

class StoreConnection(StoreConnectionMixin, Base):
    __tablename__ = "store_connections"
    __table_args__ = {"schema": "myservice"}
```

**Columns:**
- `id`: UUID (primary key)
- `user_id`: UUID (indexed, FK to users.id)
- `platform`: Enum(PlatformType)
- `store_url`: String(512)
- `store_name`: String(255)
- `credentials_encrypted`: Text (JSON blob)
- `is_active`: Boolean (default True)
- `last_synced_at`: DateTime(timezone=True) | None
- `created_at`: DateTime(timezone=True)
- `updated_at`: DateTime(timezone=True) (auto-updated on modification)

---
*See also: [README](README.md) · [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [Testing](TESTING.md)*
