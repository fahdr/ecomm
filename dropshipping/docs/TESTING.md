# Testing Guide

> Part of [Dropshipping Platform](README.md) documentation

## Test Stack

| Tool | Purpose |
|------|---------|
| **pytest** 8.3+ | Backend test runner and assertion framework |
| **pytest-asyncio** 0.24+ | Async test support (all backend code is async) |
| **httpx** 0.28+ | HTTP client used to call API endpoints in tests |
| **Playwright** | E2E browser testing (dashboard + storefront) |
| **Ruff** 0.8+ | Python linter |
| **ESLint** | TypeScript/Next.js linter |

## Running Tests

### Backend Tests (580 tests, ~35 files)

```bash
cd /workspaces/ecomm/dropshipping/backend

python -m pytest tests/ -x          # All tests, stop on first failure
pytest -v                            # Verbose output
pytest tests/test_orders.py          # Specific file
pytest -k "checkout"                 # Keyword filter
pytest -x --tb=short                 # Short tracebacks
```

### E2E Tests (200+ tests, 25 spec files)

**Prerequisites:** Backend (8000), Dashboard (3000), Storefront (3001) must be running.

```bash
cd /workspaces/ecomm/e2e

npx playwright test                                     # All tests
npx playwright test --reporter=line                     # CI-friendly output
npx playwright test tests/dashboard/orders.spec.ts      # Specific file
npx playwright test --headed                            # Visible browser
npx playwright test --repeat-each=3                     # Flakiness check
npx playwright test --debug                             # Debug mode
```

### VS Code Integration

Tests appear in the **Test Explorer** sidebar. Click play to run/debug. Breakpoints work in test files.

## Test Isolation (Schema-Based)

All tests use a dedicated PostgreSQL schema (`dropshipping_test`) for isolation from other services sharing the same database.

**How it works:**

1. **Session-scoped `create_tables` fixture** (runs once):
   - Terminates stale connections (filtered to `dropshipping_test` only)
   - Drops and recreates the `dropshipping_test` schema via raw asyncpg
   - Creates all tables with a fresh engine whose `search_path` is set to `dropshipping_test`
   - Overrides FastAPI `get_db` dependency

2. **Per-test `truncate_tables` fixture**:
   - Disposes engine to release pooled connections
   - Truncates all tables within `dropshipping_test`
   - Retries up to 3 times on transient errors

3. **`search_path` enforcement**:
   - SQLAlchemy `connect` event listener sets `SET search_path TO dropshipping_test`
   - Any test file with its own DB engine **must** also set `search_path`

## Test Coverage

### Backend (40 files, 580 tests)

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_health.py` | 1 | Health endpoint |
| `test_auth.py` | 15 | Registration, login, refresh, me, forgot-password |
| `test_stores.py` | 20 | CRUD, slugs, tenant isolation, soft-delete |
| `test_products.py` | 24 | CRUD, variants, search, pagination, images |
| `test_orders.py` | 21+ | Checkout, fulfillment, status, notes |
| `test_public.py` | 6+ | Public store/product resolution, 404s |
| `test_bridge_tasks.py` | 16 | ServiceBridge Celery tasks, HMAC, delivery recording |
| `test_bridge_service.py` | 10 | HMAC signing, fire_platform_event, queries |
| `test_bridge_api.py` | 13 | Bridge API endpoints, auth, pagination, dispatch |
| `test_subscriptions.py` | — | Subscription checkout, portal, plan limits |
| `test_categories.py` | — | Category CRUD, nesting, product counts |
| `test_discounts.py` | — | Discount code CRUD, validation, expiry |
| `test_reviews.py` | — | Review CRUD, moderation, ratings |
| `test_themes.py` | — | Theme CRUD, preset seeding, block config |
| `test_customers.py` | — | Customer auth, addresses, wishlist |
| `test_analytics.py` | — | Revenue/order/product analytics |
| *+ 24 more files* | — | Gift cards, segments, teams, tax, currency, domains, fraud, suppliers, bulk, search, webhooks, notifications, upsells, A/B tests, email/fraud/order/notification/webhook tasks, services |

### E2E (25 spec files, 200+ tests)

**Dashboard (19 specs):** auth, stores, orders, fulfillment, products, categories, discounts, themes-email, reviews-analytics, phase2-polish, billing, gift-cards, suppliers, tax-refunds, currency-domain, advanced-features, teams-webhooks, seed-data, service-bridge

**Storefront (6 specs):** browse, cart-checkout, categories-search, customer-accounts, policies, seed-data

## Fixtures

**`client`** — Async HTTP client wired to FastAPI (no network):
```python
@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
```

**`db`** — Raw async database session:
```python
@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with _session_factory() as session:
        yield session
```

## E2E Test Helpers (`helpers.ts`)

| Helper | Purpose |
|--------|---------|
| `registerUser()` | Creates user, returns `{ email, password, token }` |
| `dashboardLogin(page, email, password)` | Logs into dashboard UI |
| `createStoreAPI(token)` | Creates store via API, returns `{ id, slug }` |
| `createProductAPI(token, storeId, options?)` | Creates product with variants |
| `createOrderAPI(storeSlug, email, items)` | Creates checkout order |
| `updateOrderStatusAPI(token, storeId, orderId, status)` | Updates order status |

## Writing Tests

### Backend Test Example

```python
import pytest

@pytest.mark.asyncio
async def test_create_widget(client):
    """Verify authenticated users can create widgets."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com", "password": "testpass123"
    })
    token = reg.json()["access_token"]
    response = await client.post(
        "/api/v1/widgets", json={"name": "Test Widget"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
```

### E2E Test Example

```typescript
import { test, expect } from "@playwright/test";
import { registerUser, dashboardLogin, createStoreAPI } from "../helpers";

test.describe("Widget Feature", () => {
  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    const store = await createStoreAPI(user.token);
    await dashboardLogin(page, user.email, user.password);
  });

  test("shows widget list", async ({ page }) => {
    await expect(page.getByText(/widgets/i).first()).toBeVisible({ timeout: 10000 });
  });
});
```

### E2E Best Practices

- Use `.first()` when multiple elements might match (strict mode)
- Use `{ exact: true }` for exact text matching
- Use `{ timeout: 10000 }` for assertions waiting on network data
- Use `waitForLoadState("networkidle")` before interacting with dynamic pages
- Include `shipping_address` in checkout payloads

## Configuration

Backend (`pyproject.toml`):
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

E2E (`playwright.config.ts`): Chromium, base URL `http://localhost:3000`, parallel execution.

## Known Flaky Tests

| Test | Reason | Workaround |
|------|--------|-----------|
| `themes-email.spec.ts` > sidebar nav | Timeout loading theme list | Increase timeout or retry |
| `Command Palette > closes on Escape` | Input focus timing | Runs reliably in isolation |

## Linting

```bash
cd /workspaces/ecomm/dropshipping/backend && ruff check .        # Python check
cd /workspaces/ecomm/dropshipping/backend && ruff check --fix .  # Python fix
cd /workspaces/ecomm/dropshipping/dashboard && npm run lint       # Dashboard
cd /workspaces/ecomm/dropshipping/storefront && npm run lint      # Storefront
```

---
*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [QA Engineer Guide](QA_ENGINEER.md)*
