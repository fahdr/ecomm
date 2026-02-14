# Setup Guide

> Part of [ecomm_connectors](README.md) documentation

This guide covers installation, configuration, and integration patterns for the `ecomm_connectors` package.

## Installation

### From Source (Editable Install)

Install the package in development mode from the monorepo root:

```bash
pip install -e packages/py-connectors
```

This creates an editable installation that reflects source changes immediately.

### Dependencies

The package requires Python 3.12+ and these core dependencies:

- **httpx** (0.27+): Async HTTP client for platform API calls
- **SQLAlchemy** (2.0+): ORM for `store_connections` table schema
- **Pydantic** (2.0+): Request/response validation schemas

Development dependencies (optional):

```bash
pip install -e "packages/py-connectors[dev]"
```

Installs pytest, pytest-asyncio, and respx for testing.

## Import Patterns

### Factory Function (Recommended)

Use `get_connector()` to obtain the correct adapter based on platform type:

```python
from ecomm_connectors.factory import get_connector
from ecomm_connectors.base import PlatformType

connector = get_connector(
    PlatformType.shopify,
    "https://mystore.myshopify.com",
    {"access_token": "shpat_xxxx"}
)
```

Accepts either `PlatformType` enum or string ("shopify", "woocommerce", "platform").

### Direct Import (Advanced)

For type hints or explicit imports:

```python
from ecomm_connectors.shopify import ShopifyConnector
from ecomm_connectors.woocommerce import WooCommerceConnector
from ecomm_connectors.platform import PlatformConnector

connector = ShopifyConnector(store_url, credentials)
```

### Normalized Types

Import data classes for type annotations:

```python
from ecomm_connectors.base import (
    NormalizedProduct,
    NormalizedOrder,
    NormalizedCustomer,
    ConnectionTestResult,
    ConnectorError
)

async def sync_products(connector) -> list[NormalizedProduct]:
    products, cursor = await connector.fetch_products()
    return products
```

## Usage in Services

### Basic Integration Pattern

Services typically store connection credentials in the database and create connectors on demand:

```python
from ecomm_connectors.factory import get_connector
from ecomm_connectors.base import ConnectorError
from sqlalchemy.ext.asyncio import AsyncSession

async def fetch_store_products(connection_id: str, db: AsyncSession):
    # Fetch connection from DB
    conn = await db.get(StoreConnection, connection_id)
    if not conn or not conn.is_active:
        raise ValueError("Connection not found or inactive")

    # Decrypt credentials (implementation-specific)
    credentials = decrypt_credentials(conn.credentials_encrypted)

    # Get connector
    connector = get_connector(conn.platform, conn.store_url, credentials)

    # Fetch products with pagination
    all_products = []
    cursor = None
    while True:
        products, cursor = await connector.fetch_products(
            limit=100, cursor=cursor
        )
        all_products.extend(products)
        if not cursor:
            break

    return all_products
```

### Error Handling

All connector methods raise `ConnectorError` on failures:

```python
from ecomm_connectors.base import ConnectorError

try:
    result = await connector.test_connection()
    if not result.success:
        print(f"Connection test failed: {result.message}")
except ConnectorError as e:
    print(f"HTTP {e.status_code}: {e.platform} - {str(e)}")
```

### Storing Connection Info

Use `StoreConnectionMixin` to add the schema to your service's SQLAlchemy models:

```python
from ecomm_core.models.base import Base
from ecomm_connectors.models import StoreConnectionMixin

class StoreConnection(StoreConnectionMixin, Base):
    __tablename__ = "store_connections"
    __table_args__ = {"schema": "myservice"}
```

This creates a table with columns: `id`, `user_id`, `platform`, `store_url`, `store_name`, `credentials_encrypted`, `is_active`, `last_synced_at`, `created_at`, `updated_at`.

### API Endpoint Pattern

Example FastAPI endpoint for connecting a store:

```python
from fastapi import APIRouter, Depends
from ecomm_connectors.factory import get_connector
from ecomm_connectors.schemas import ConnectStoreRequest, TestConnectionResponse

router = APIRouter(prefix="/connections", tags=["connections"])

@router.post("/test", response_model=TestConnectionResponse)
async def test_connection(req: ConnectStoreRequest):
    """Test a store connection before saving."""
    connector = get_connector(req.platform, req.store_url, req.credentials)
    result = await connector.test_connection()
    return TestConnectionResponse(
        success=result.success,
        platform=result.platform,
        store_name=result.store_name,
        message=result.message
    )
```

## Configuration

No global configuration is required. Each connector receives credentials at initialization and operates independently.

### Credential Requirements

**Shopify:**
```python
credentials = {"access_token": "shpat_..."}
```

**WooCommerce:**
```python
credentials = {
    "consumer_key": "ck_...",
    "consumer_secret": "cs_..."
}
```

**Platform:**
```python
credentials = {"api_key": "..."}
```

Missing credentials raise `ConnectorError` on init.

### Environment Variables (Service Level)

Services handle credential encryption/decryption using their own secret keys:

```bash
# Example service .env
ENCRYPTION_KEY=your-fernet-key-here
```

The connectors package itself does not read environment variables.

---
*See also: [README](README.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
