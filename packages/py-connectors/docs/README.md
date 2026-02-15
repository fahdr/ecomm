# ecomm_connectors

> **Connector library for e-commerce platform integrations**

Platform-agnostic adapters for Shopify, WooCommerce, and the internal dropshipping platform. All connectors share a common interface (`AbstractPlatformConnector`) with normalized data types for products, orders, and customers.

## Overview

`ecomm_connectors` provides a unified API for syncing data across multiple e-commerce platforms. Services use the factory function `get_connector()` to obtain the correct adapter based on platform type, then call standardized methods like `fetch_products()`, `fetch_orders()`, and `test_connection()`.

**Key Features:**
- Abstract base class ensures consistent API across all platforms
- Normalized data types (`NormalizedProduct`, `NormalizedOrder`, `NormalizedCustomer`)
- Automatic pagination handling (Link headers for Shopify, page offsets for WooCommerce/Platform)
- Rate limit retries for Shopify (429 responses)
- Platform-specific credential validation on init
- SQLAlchemy model mixin for `store_connections` table

## Supported Platforms

| Platform | Type Enum | Required Credentials |
|----------|-----------|---------------------|
| Shopify | `PlatformType.shopify` | `access_token` |
| WooCommerce | `PlatformType.woocommerce` | `consumer_key`, `consumer_secret` |
| Dropshipping Platform | `PlatformType.platform` | `api_key` |

## Quick Start

```python
from ecomm_connectors.factory import get_connector
from ecomm_connectors.base import PlatformType

# Get a connector for the platform
connector = get_connector(
    PlatformType.shopify,
    "https://mystore.myshopify.com",
    {"access_token": "shpat_xxxx"}
)

# Test the connection
result = await connector.test_connection()
print(result.store_name)  # "My Store"

# Fetch products with pagination
products, next_cursor = await connector.fetch_products(limit=50)
for product in products:
    print(f"{product.title}: ${product.price}")
```

## Metrics

- **Tests:** 40 passing (100% coverage)
- **Dependencies:** httpx, SQLAlchemy, Pydantic
- **Python Version:** 3.12+

## Documentation

- [Setup](SETUP.md) — Installation and integration patterns
- [Architecture](ARCHITECTURE.md) — Adapter pattern and design decisions
- [API Reference](API_REFERENCE.md) — Complete API documentation
- [Testing](TESTING.md) — Test stack and coverage details

---
*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
