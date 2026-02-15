# Architecture

> Part of [ecomm_connectors](README.md) documentation

This document describes the design patterns, component relationships, and architectural decisions for the `ecomm_connectors` package.

## Design Goals

1. **Platform Independence**: Services use a single interface regardless of backend platform
2. **Normalized Data**: All connectors return the same data types (`NormalizedProduct`, etc.)
3. **Pagination Abstraction**: Hide platform-specific pagination (Link headers vs page numbers)
4. **Error Consistency**: Single exception type (`ConnectorError`) for all platforms
5. **Schema Reuse**: Share `store_connections` table structure across services

## Adapter Pattern

The package implements the Adapter pattern to unify three e-commerce APIs behind a common interface.

`AbstractPlatformConnector` defines the contract all connectors must implement: `test_connection()`, `fetch_products()`, `fetch_orders()`, `fetch_customers()`, `push_product_update()`, `create_product()`.

**Concrete Implementations:**

- **ShopifyConnector**: REST Admin API v2024-01, `X-Shopify-Access-Token` auth, Link-header pagination, 429 retry
- **WooCommerceConnector**: REST API v3, query-string auth, offset pagination, `X-WP-TotalPages` header
- **PlatformConnector**: Internal API, Bearer token auth, `{"items": [...], "total": N}` response format

## Normalized Data Types

All connectors map platform-specific responses to common dataclasses:

- **NormalizedProduct**: `external_id`, `title`, `description`, `price` (string), `currency`, `sku`, `inventory_quantity`, `images`, `url`, `vendor`, `tags`, `raw`
- **NormalizedOrder**: `external_id`, `order_number`, `email`, `total` (string), `currency`, `status`, `line_items`, `created_at`, `raw`
- **NormalizedCustomer**: `external_id`, `email`, `first_name`, `last_name`, `total_orders`, `total_spent` (string), `tags`, `raw`

The `raw` field preserves the original platform response for debugging and platform-specific fields.

## Pagination Strategy

Each platform implements pagination differently. Connectors abstract this behind a common cursor-based API:

**Cursor Semantics:**
- `cursor=None`: Fetch first page
- `cursor=str`: Platform-specific continuation token
- Return `(items, next_cursor)` where `next_cursor=None` means no more pages

**Platform Implementations:**

| Platform | Cursor Type | Implementation |
|----------|-------------|----------------|
| Shopify | Full URL | Parses `Link: <url>; rel="next"` header |
| WooCommerce | Page number (string) | Increments page, checks `X-WP-TotalPages` |
| Platform | Page number (string) | Increments page, compares `page * limit < total` |

**Usage Example:**
```python
all_products = []
cursor = None
while True:
    products, cursor = await connector.fetch_products(limit=100, cursor=cursor)
    all_products.extend(products)
    if not cursor:
        break
```

## Factory Pattern

`get_connector()` function maps `PlatformType` enum to the correct connector class:

```python
def get_connector(
    platform: PlatformType | str,
    store_url: str,
    credentials: dict[str, str]
) -> AbstractPlatformConnector:
    connectors = {
        PlatformType.shopify: ShopifyConnector,
        PlatformType.woocommerce: WooCommerceConnector,
        PlatformType.platform: PlatformConnector,
    }

    connector_class = connectors.get(platform)
    if not connector_class:
        raise ConnectorError(f"Unsupported platform: {platform}")

    return connector_class(store_url, credentials)
```

This pattern allows services to work with platform types without importing connector classes directly.

## Error Handling

`ConnectorError` exception wraps all platform-specific errors:

```python
class ConnectorError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        platform: str = ""
    )
```

**Raised for:**
- Missing credentials on init
- HTTP errors (4xx, 5xx)
- Parsing failures
- Network timeouts

**Not raised for:**
- Empty result sets (returns empty list)
- Successful connection tests that fail auth (returns `ConnectionTestResult(success=False)`)

## Schema Design

### StoreConnectionMixin

SQLAlchemy mixin provides consistent schema across services:

```python
class StoreConnectionMixin:
    id: UUID (primary key)
    user_id: UUID (indexed, FK to users.id)
    platform: Enum(PlatformType)
    store_url: String(512)
    store_name: String(255)
    credentials_encrypted: Text  # JSON-encoded, service encrypts
    is_active: Boolean (default True)
    last_synced_at: DateTime(timezone=True) | None
    created_at: DateTime(timezone=True)
    updated_at: DateTime(timezone=True)
```

**Usage:**
```python
from ecomm_core.models.base import Base
from ecomm_connectors.models import StoreConnectionMixin

class StoreConnection(StoreConnectionMixin, Base):
    __tablename__ = "store_connections"
    __table_args__ = {"schema": "myservice"}
```

Each service inherits this mixin and sets its own schema to avoid table conflicts.

### Pydantic Schemas

Request/response DTOs: `ConnectStoreRequest`, `StoreConnectionResponse`, `TestConnectionResponse`, `SyncStatusResponse`.

## Design Decisions

### Why Cursor Strings Instead of Offset Integers?

Cursor strings support both URL-based (Shopify) and offset-based (WooCommerce/Platform) pagination without leaking implementation details to callers.

### Why Store `raw` Payload?

Preserves the original platform response for debugging, allows services to access platform-specific fields not covered by normalized schema.

### Why Not Use GraphQL for Shopify?

The REST Admin API is simpler, requires fewer dependencies, and provides sufficient functionality for batch sync operations.

### Why Text Column for Credentials?

SQLAlchemy Text type avoids JSON encoding issues. Services handle encryption at application layer using their own keys (not database-level encryption).

---
*See also: [README](README.md) · [Setup](SETUP.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
