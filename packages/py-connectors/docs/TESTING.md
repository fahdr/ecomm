# Testing

> Part of [ecomm_connectors](README.md) documentation

This guide covers the test stack, running tests, and coverage details for the `ecomm_connectors` package.

## Test Stack

The package uses:

- **pytest** (8.0+): Test framework
- **pytest-asyncio** (0.24+): Async test support (`asyncio_mode = "auto"`)
- **respx** (0.21+): HTTP request mocking for httpx

All tests run without external dependencies — no real API credentials or network calls required.

## Running Tests

### Full Test Suite

From the package directory:

```bash
cd packages/py-connectors
pytest
```

Expected output:
```
======================== 40 passed, 1 warning in 0.96s =========================
```

### Verbose Mode

```bash
pytest -v
```

Shows individual test names and outcomes.

### Single Test File

```bash
pytest tests/test_connectors.py
```

### Specific Test Class

```bash
pytest tests/test_connectors.py::TestShopifyConnector
```

### Specific Test Method

```bash
pytest tests/test_connectors.py::TestShopifyConnector::test_fetch_products
```

### Coverage Report

```bash
pytest --cov=ecomm_connectors --cov-report=term-missing
```

Shows line-by-line coverage for all modules.

## Test Coverage

### Summary (40 tests)

| Component | Test Count | Coverage |
|-----------|------------|----------|
| Factory | 4 | 100% |
| Credential Validation | 4 | 100% |
| Shopify Connector | 10 | 100% |
| WooCommerce Connector | 9 | 100% |
| Platform Connector | 6 | 100% |
| Schemas | 2 | 100% |
| Models | 1 | 100% |
| Normalized Types | 4 | 100% |

### Coverage by File

| File | Lines | Covered | % |
|------|-------|---------|---|
| `base.py` | 276 | 276 | 100% |
| `factory.py` | 76 | 76 | 100% |
| `shopify.py` | 370 | 370 | 100% |
| `woocommerce.py` | 337 | 337 | 100% |
| `platform.py` | 333 | 333 | 100% |
| `schemas.py` | 114 | 114 | 100% |
| `models.py` | 82 | 82 | 100% |
| **Total** | **1,588** | **1,588** | **100%** |

## Test Organization

### Test Classes

**`TestFactory`** (4 tests): Verifies `get_connector()` returns correct class for each platform, accepts strings, raises on unknown types

**`TestCredentialValidation`** (4 tests): Ensures connectors raise `ConnectorError` on missing credentials

**`TestShopifyConnector`** (10 tests): Connection test, fetch products/orders/customers, pagination (Link header), create/update, rate limit retry on 429

**`TestWooCommerceConnector`** (9 tests): Connection test, fetch products/orders/customers, pagination (page numbers, `X-WP-TotalPages`), create/update, API error handling

**`TestPlatformConnector`** (6 tests): Connection test, fetch products/orders/customers with `{"items": [...], "total": N}` format, pagination, create product

**`TestSchemas`** (2 tests): Validates Pydantic request/response schemas

**`TestModelMixin`** (1 test): Verifies `StoreConnectionMixin` columns exist

**`TestNormalizedTypes`** (4 tests): Tests dataclass defaults and `ConnectorError` attributes

## Mock Patterns

All tests use `respx.mock` decorator to intercept HTTP calls without hitting real APIs:

```python
@respx.mock
@pytest.mark.asyncio
async def test_fetch_products(self):
    respx.get(url).mock(return_value=httpx.Response(200, json={...}))
    products, cursor = await connector.fetch_products()
```

Use `side_effect` for multiple responses (pagination, retries):

```python
route = respx.get(url)
route.side_effect = [
    httpx.Response(429, headers={"Retry-After": "0.01"}),
    httpx.Response(200, json={"shop": {"name": "Store"}}),
]
```

## CI Integration

Tests run automatically in GitHub Actions with coverage reporting to Codecov.

---
*See also: [README](README.md) · [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md)*
