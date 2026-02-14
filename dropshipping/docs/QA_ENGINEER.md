# QA Engineer Guide — Dropshipping Platform

**For QA Engineers:**
This guide covers the full testing infrastructure, test coverage, testing patterns, and verification procedures for the Dropshipping Platform.

## Test Stack

| Tool | Purpose |
|------|---------|
| **pytest** 8.3+ | Backend test runner and assertion framework |
| **pytest-asyncio** 0.24+ | Async test support (all backend code is async) |
| **httpx** 0.28+ | HTTP client used to call API endpoints in tests |
| **Playwright** | E2E browser testing (dashboard + storefront) |
| **Ruff** 0.8+ | Python linter — catches code quality issues |
| **ESLint** | TypeScript/Next.js linter |

## Running Tests

### Backend Tests (580 tests)

```bash
cd /workspaces/ecomm/dropshipping/backend

# Run all tests (stop on first failure)
python -m pytest tests/ -x

# Verbose output (see each test name and result)
pytest -v

# Run a specific test file
pytest tests/test_orders.py

# Run tests matching a keyword
pytest -k "checkout"

# Run with short tracebacks
pytest -x --tb=short
```

### E2E Tests (200+ tests, 25 spec files)

**Prerequisites:** Start all three services before running E2E tests:
1. Backend API on port 8000
2. Dashboard on port 3000
3. Storefront on port 3001

```bash
cd /workspaces/ecomm/e2e

# Run all e2e tests
npx playwright test

# Run with line reporter (CI-friendly, less verbose)
npx playwright test --reporter=line

# Run specific spec file
npx playwright test tests/dashboard/orders.spec.ts

# Run specific test suite
npx playwright test tests/dashboard/

# Run headed (visible browser window)
npx playwright test --headed

# Run with repeat to check flakiness
npx playwright test tests/dashboard/phase2-polish.spec.ts --repeat-each=3

# Run with debug mode
npx playwright test --debug
```

### VS Code Integration

The devcontainer configures pytest in VS Code automatically:
- Tests appear in the **Test Explorer** sidebar
- Click the play button next to any test to run or debug it
- Breakpoints work in test files

## Current Test Coverage

### Backend Test Files (40 files, 580 tests)

| Test File | Tests | What it covers |
|-----------|-------|----------------|
| `test_health.py` | 1 | `GET /api/v1/health` returns 200 with status ok |
| `test_auth.py` | 15 | Registration, login, token refresh, `/me`, forgot-password, invalid credentials, expired tokens |
| `test_stores.py` | 20 | Store CRUD, slug uniqueness, tenant isolation, soft-delete, auth required |
| `test_products.py` | 24 | Product CRUD, variants, slug collision, pagination, search, status filter, image upload, public endpoints |
| `test_orders.py` | 21+ | Checkout, fulfillment, status transitions, order notes, tenant isolation, public order lookup |
| `test_public.py` | 6+ | Public store/product resolution, user_id exclusion, 404 for unknown/paused/deleted stores |
| `test_subscriptions.py` | -- | Subscription checkout, portal, plan limits |
| `test_categories.py` | -- | Category CRUD, nesting, product counts |
| `test_discounts.py` | -- | Discount code CRUD, validation, expiry |
| `test_reviews.py` | -- | Review CRUD, moderation, ratings |
| `test_refunds.py` | -- | Refund processing, partial refunds |
| `test_themes.py` | -- | Theme CRUD, preset seeding, block config |
| `test_analytics.py` | -- | Revenue/order/product analytics queries |
| `test_analytics_tasks.py` | -- | Celery analytics background tasks |
| `test_customers.py` | -- | Customer auth, addresses, wishlist |
| `test_gift_cards.py` | -- | Gift card creation, redemption |
| `test_segments.py` | -- | Customer segment CRUD |
| `test_upsells.py` | -- | Upsell recommendation management |
| `test_teams.py` | -- | Team member invitation, roles |
| `test_tax.py` | -- | Tax rule configuration |
| `test_currency.py` | -- | Currency settings |
| `test_domains.py` | -- | Custom domain management |
| `test_fraud.py` | -- | Fraud detection rules |
| `test_fraud_tasks.py` | -- | Celery fraud detection tasks |
| `test_suppliers.py` | -- | Supplier CRUD |
| `test_bulk.py` | -- | Bulk product operations |
| `test_search.py` | -- | Full-text search across products |
| `test_store_webhooks.py` | -- | Webhook configuration and delivery |
| `test_webhook_tasks.py` | -- | Celery webhook delivery tasks |
| `test_ab_tests.py` | -- | A/B test experiment management |
| `test_notifications.py` | -- | Notification CRUD and read status |
| `test_notification_tasks.py` | -- | Celery notification tasks |
| `test_order_tasks.py` | -- | Celery order processing tasks |
| `test_email_tasks.py` | -- | Celery email delivery tasks |
| `test_services.py` | -- | Service integration endpoints |
| `test_service_schemas.py` | -- | Service schema validation |
| `test_service_integration_service.py` | -- | Service integration business logic |
| `test_bridge_tasks.py` | 16 | ServiceBridge Celery tasks: event routing, delivery recording, HMAC signing, error handling |
| `test_bridge_service.py` | 10 | ServiceBridge service layer: HMAC signing, fire_platform_event, empty result queries |
| `test_bridge_api.py` | 13 | ServiceBridge API endpoints: auth enforcement, pagination, filtering, manual dispatch |

### E2E Test Files (25 spec files, 200+ tests)

#### Dashboard Tests (19 spec files)

| Spec File | What it covers |
|-----------|----------------|
| `auth.spec.ts` | Login, registration, logout, token refresh, protected routes |
| `stores.spec.ts` | Store creation, listing, editing, deletion |
| `orders.spec.ts` | Order listing, filtering, status display |
| `fulfillment.spec.ts` | Fulfillment form, tracking numbers, ship/deliver lifecycle, shipping address display |
| `products.spec.ts` | Product creation, editing, variant management |
| `categories.spec.ts` | Category creation, product assignment |
| `discounts.spec.ts` | Discount code creation, validation |
| `themes-email.spec.ts` | Theme selection, preset application, email templates |
| `reviews-analytics.spec.ts` | Review display, analytics metrics, charts |
| `phase2-polish.spec.ts` | Platform home KPIs, store overview KPIs, order notes, CSV export, command palette, inventory alerts |
| `billing.spec.ts` | Subscription management, plan display |
| `gift-cards.spec.ts` | Gift card creation and management |
| `suppliers.spec.ts` | Supplier management |
| `tax-refunds.spec.ts` | Tax settings, refund processing |
| `currency-domain.spec.ts` | Currency and domain configuration |
| `advanced-features.spec.ts` | A/B tests, segments, bulk ops, fraud, upsells |
| `teams-webhooks.spec.ts` | Team and webhook management |
| `seed-data.spec.ts` | Seed data validation (Volt Electronics) |
| `service-bridge.spec.ts` | ServiceBridge activity, dispatch, service cards, product panels, sidebar |

#### Storefront Tests (6 spec files)

| Spec File | What it covers |
|-----------|----------------|
| `browse.spec.ts` | Homepage, product listing, product detail, navigation |
| `cart-checkout.spec.ts` | Add to cart, cart management, checkout flow |
| `categories-search.spec.ts` | Category browsing, search functionality |
| `customer-accounts.spec.ts` | Customer registration, login, account pages |
| `policies.spec.ts` | Legal policy pages |
| `seed-data.spec.ts` | Seed data validation from storefront perspective |

## Test Structure

### Backend Test Directory

```
dropshipping/backend/tests/
├── __init__.py
├── conftest.py                        # Shared fixtures (schema isolation, client, DB cleanup)
├── test_health.py                     # Health endpoint (1 test)
├── test_auth.py                       # Auth endpoints (15 tests)
├── test_stores.py                     # Store CRUD (20 tests)
├── test_products.py                   # Product CRUD (24 tests)
├── test_orders.py                     # Order management (21+ tests)
├── test_public.py                     # Public API (6+ tests)
├── test_customers.py                  # Customer accounts
├── test_refunds.py                    # Refund processing
├── test_themes.py                     # Theme management
├── test_reviews.py                    # Review system
├── test_analytics.py                  # Analytics queries
├── test_analytics_tasks.py            # Celery analytics tasks
├── test_email_tasks.py                # Celery email tasks
├── test_fraud_tasks.py                # Celery fraud tasks
├── test_notification_tasks.py         # Celery notification tasks
├── test_order_tasks.py                # Celery order tasks
├── test_webhook_tasks.py              # Celery webhook tasks
├── test_subscriptions.py              # Subscription management
├── test_categories.py                 # Category CRUD
├── test_discounts.py                  # Discount management
├── test_gift_cards.py                 # Gift cards
├── test_segments.py                   # Customer segments
├── test_upsells.py                    # Upsell recommendations
├── test_teams.py                      # Team members
├── test_tax.py                        # Tax rules
├── test_currency.py                   # Currency settings
├── test_domains.py                    # Domain management
├── test_fraud.py                      # Fraud detection
├── test_suppliers.py                  # Supplier CRUD
├── test_bulk.py                       # Bulk product ops
├── test_search.py                     # Full-text search
├── test_store_webhooks.py             # Webhook config
├── test_ab_tests.py                   # A/B test experiments
├── test_notifications.py              # Notification CRUD
├── test_services.py                   # Service integrations
├── test_service_schemas.py            # Service schema validation
├── test_service_integration_service.py # Service integration logic
├── test_bridge_tasks.py               # ServiceBridge Celery tasks (16 tests)
├── test_bridge_service.py             # ServiceBridge service layer (10 tests)
└── test_bridge_api.py                 # ServiceBridge API endpoints (13 tests)
```

### E2E Test Directory

```
e2e/
├── tests/
│   ├── helpers.ts                 # Shared utilities
│   ├── dashboard/                 # 19 spec files
│   │   ├── auth.spec.ts
│   │   ├── stores.spec.ts
│   │   ├── orders.spec.ts
│   │   ├── fulfillment.spec.ts
│   │   ├── phase2-polish.spec.ts
│   │   ├── service-bridge.spec.ts
│   │   └── ... (13 more)
│   └── storefront/                # 6 spec files
│       ├── browse.spec.ts
│       ├── cart-checkout.spec.ts
│       └── ... (4 more)
├── playwright.config.ts
└── package.json
```

## Fixtures

### Schema-Based Test Isolation (`conftest.py`)

All tests use a dedicated PostgreSQL schema (`dropshipping_test`) to isolate the dropshipping service from other services sharing the same database. This replaces the older `clean_tables` approach that used `pg_terminate_backend` on all connections.

**How it works:**

1. **Session-scoped `create_tables` fixture** (runs once per test session):
   - Terminates stale connections from prior test runs (filtered to `dropshipping_test` queries only, never kills other services' connections)
   - Drops and recreates the `dropshipping_test` schema via raw asyncpg
   - Creates all tables with a fresh SQLAlchemy engine whose `search_path` is set to `dropshipping_test`
   - Wires up the FastAPI `get_db` dependency override to use the test engine

2. **Per-test `truncate_tables` fixture** (runs before each test):
   - Disposes the app's engine to release pooled connections
   - Truncates all tables within the `dropshipping_test` schema for data isolation
   - Retries up to 3 times on transient connection errors

3. **`search_path` enforcement**:
   - A SQLAlchemy `connect` event listener sets `SET search_path TO dropshipping_test` on every new raw connection
   - Any test file with its own DB engine **must** also set `search_path` to the test schema

**`client` fixture** — Provides an async HTTP client wired directly to the FastAPI app (no network required). The `get_db` dependency is overridden at session scope by `create_tables`:

```python
@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an httpx AsyncClient for API testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
```

**`db` fixture** — Provides a raw async database session for tests that need direct DB access:

```python
@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session for tests."""
    async with _session_factory() as session:
        yield session
```

## E2E Test Helpers

### Shared Functions (`helpers.ts`)

| Helper | Purpose |
|--------|---------|
| `registerUser()` | Creates a new user account, returns `{ email, password, token }` |
| `dashboardLogin(page, email, password)` | Logs into the dashboard UI |
| `createStoreAPI(token)` | Creates a test store via API, returns `{ id, slug }` |
| `createProductAPI(token, storeId, options?)` | Creates a test product with variants |
| `createOrderAPI(storeSlug, email, items)` | Creates a checkout order |
| `updateOrderStatusAPI(token, storeId, orderId, status)` | Updates order status via API |

## Writing Tests

### Writing a Backend Test

```python
"""
Tests for the widget feature.

**For Developers:**
  Covers CRUD operations and edge cases for the widget endpoints.

**For QA Engineers:**
  Validates widget creation, retrieval, update, and deletion
  with proper authorization and tenant isolation.
"""
import pytest

@pytest.mark.asyncio
async def test_create_widget(client):
    """Verify that authenticated users can create widgets."""
    # Register and get token
    reg = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com", "password": "testpass123"
    })
    token = reg.json()["access_token"]

    # Create widget
    response = await client.post(
        "/api/v1/widgets",
        json={"name": "Test Widget"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
```

### Writing an E2E Test

```typescript
/**
 * Widget feature e2e tests.
 *
 * **For QA Engineers:**
 *   - Widget list shows created widgets.
 *   - Widget creation form validates required fields.
 */
import { test, expect } from "@playwright/test";
import { registerUser, dashboardLogin, createStoreAPI } from "../helpers";

test.describe("Widget Feature", () => {
  let email: string;
  let password: string;
  let token: string;
  let storeId: string;

  test.beforeEach(async ({ page }) => {
    const user = await registerUser();
    email = user.email;
    password = user.password;
    token = user.token;
    const store = await createStoreAPI(token);
    storeId = store.id;
    await dashboardLogin(page, email, password);
  });

  test("shows widget list", async ({ page }) => {
    await page.goto(`/stores/${storeId}/widgets`);
    await expect(page.getByText(/widgets/i).first()).toBeVisible({ timeout: 10000 });
  });
});
```

### E2E Best Practices

- **Use `.first()`** when multiple elements might match (Playwright strict mode throws on ambiguous selectors)
- **Use `{ exact: true }`** for exact text matching to avoid partial matches
- **Use `{ timeout: 10000 }`** for assertions that wait for network data to load
- **Use `waitForLoadState("networkidle")`** before interacting with dynamic pages
- **Include `shipping_address`** in checkout payloads (required after Phase A enhancement)
- **Handle paginated responses** — API returns `{ items: [...] }` format, not bare arrays

## Configuration

Backend (`pyproject.toml`):

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"      # No need for @pytest.mark.asyncio on every test
testpaths = ["tests"]       # pytest looks here by default
```

E2E (`playwright.config.ts`):
- Chromium browser by default
- Base URL: `http://localhost:3000` (dashboard)
- Parallel test execution across spec files

## ServiceBridge Tests

The ServiceBridge feature connects the dropshipping platform to 8 external SaaS services. It has 39 backend tests across three files.

### test_bridge_tasks.py (16 tests)

- Event-to-service mapping verification for all 5 event types
- Successful delivery recording
- HTTP error handling and timeout handling
- HMAC signature correctness
- Mixed results (some succeed, some fail)
- Missing base URL handling

### test_bridge_service.py (10 tests)

- HMAC signing determinism and secret variation
- `fire_platform_event` correct Celery `.delay()` arguments
- Empty result queries (activity, resource, service, summary)

### test_bridge_api.py (13 tests)

- Auth required (401) on all 5 endpoints
- Empty paginated response for new users
- Pagination and filter parameter handling
- Manual dispatch fires event and returns confirmation
- Missing fields return 422 validation error

## ServiceBridge E2E Tests

### service-bridge.spec.ts (15 tests)

| Test Group | Tests | Coverage |
|-----------|-------|---------|
| Bridge API Endpoints | 7 | Activity, summary, resource, dispatch, auth, validation |
| Service Activity Page | 4 | Empty state, KPI cards, filters, back navigation |
| Services Hub | 2 | All 8 service cards, enable buttons |
| Product Detail Panel | 2 | Connected services panel, 8-service grid |
| Sidebar Navigation | 2 | Activity link visible, navigation works |

## ServiceBridge Acceptance Criteria

1. Creating a product fires `product.created` to 6 connected services
2. Updating a product fires `product.updated` to 3 services
3. Order fulfillment fires `order.shipped` to FlowSend
4. Customer registration fires `customer.created` to FlowSend
5. Each delivery is recorded with status, latency, error details
6. Dashboard activity page shows paginated delivery history
7. Filters (event, service, status) work correctly
8. Product/order detail pages show per-resource service status
9. Services hub shows health indicators per service
10. Manual dispatch endpoint fires event and returns confirmation

## ServiceBridge Edge Cases

- No connected services: event fires but nothing is delivered
- Service returns non-200: delivery recorded as failed with error
- Service times out: delivery recorded with timeout error
- Missing `platform_webhook_secret`: uses default dev secret
- Null `store_id`: supported for customer events (public endpoint)

## API Documentation

The backend auto-generates interactive API docs:

| URL | Format |
|-----|--------|
| `http://localhost:8000/docs` | Swagger UI — interactive, try-it-out interface |
| `http://localhost:8000/redoc` | ReDoc — clean read-only documentation |
| `http://localhost:8000/openapi.json` | Raw OpenAPI 3.x schema |

Use Swagger UI to manually test endpoints during exploratory testing.

### API Response Format

All endpoints follow a consistent format. Use these patterns for assertions:

#### Paginated Response

```json
{
  "items": [ ... ],
  "total": 100,
  "page": 1,
  "per_page": 20
}
```

#### Store-Scoped Endpoints

All store resources are accessed via `/api/v1/stores/{store_id}/...`. The backend enforces tenant isolation — users can only access their own stores.

#### Public Endpoints

Public storefront API at `/api/v1/public/stores/{slug}/...` requires no authentication. Sensitive fields like `user_id` and `cost` are excluded from public responses.

#### Customer Endpoints

Customer-facing API at `/api/v1/customer/...` uses separate JWT tokens from store-owner tokens.

### Current API Endpoint Summary

#### Auth Endpoints
| Method | Path | Auth |
|--------|------|------|
| `POST` | `/api/v1/auth/register` | No |
| `POST` | `/api/v1/auth/login` | No |
| `POST` | `/api/v1/auth/refresh` | No |
| `POST` | `/api/v1/auth/forgot-password` | No |
| `GET` | `/api/v1/auth/me` | Bearer JWT |

#### Store Management
| Method | Path | Auth |
|--------|------|------|
| `POST` | `/api/v1/stores` | Bearer JWT |
| `GET` | `/api/v1/stores` | Bearer JWT |
| `GET` | `/api/v1/stores/{id}` | Bearer JWT |
| `PATCH` | `/api/v1/stores/{id}` | Bearer JWT |
| `DELETE` | `/api/v1/stores/{id}` | Bearer JWT |

#### Products, Orders, Categories, Themes, etc.
Each feature follows the same CRUD pattern scoped to `/api/v1/stores/{store_id}/...`. See Swagger UI at `/docs` for the complete 100+ endpoint listing.

#### Export Endpoints
| Method | Path | Auth |
|--------|------|------|
| `GET` | `/api/v1/stores/{id}/orders/export?format=csv` | Bearer JWT |
| `GET` | `/api/v1/stores/{id}/products/export?format=csv` | Bearer JWT |
| `GET` | `/api/v1/stores/{id}/customers/export?format=csv` | Bearer JWT |

## Seed Data & Demo Credentials

### Running the Seed Script

Before manual testing, seed the database with demo data:

```bash
# Ensure the backend is running on port 8000 with migrations applied
cd /workspaces/ecomm
npx tsx scripts/seed.ts
```

The script is **idempotent** — safe to re-run. It creates a fully populated "Volt Electronics" store with 12 products, 4 orders, 3 customers, reviews, themes, and all platform features configured.

### Demo Credentials

| Role | Email | Password | URL |
|------|-------|----------|-----|
| **Store Owner** | `demo@example.com` | `password123` | Dashboard: `http://localhost:3000` |
| **Customer (Alice)** | `alice@example.com` | `password123` | Storefront: `http://localhost:3001?store=volt-electronics` |
| **Customer (Bob)** | `bob@example.com` | `password123` | Storefront: `http://localhost:3001?store=volt-electronics` |
| **Customer (Carol)** | `carol@example.com` | `password123` | Storefront: `http://localhost:3001?store=volt-electronics` |

### What to Verify After Seeding

| Feature | How to check |
|---------|-------------|
| Sale badges | Products page -> ProBook, Galaxy Nova, SoundStage, FlexiDock show "Sale" badge (have `compare_at_price`) |
| New badges | Recently seeded products show "New" badge on storefront |
| Inventory alerts | Store overview -> NovaBand and MagFloat show "Low Stock" warnings (2-4 units) |
| Order lifecycle | Orders page -> Alice (shipped), Bob (delivered), Carol & Dave (paid/awaiting fulfillment) |
| Order notes | Open any order -> "Internal Notes" section has pre-filled notes |
| Theme blocks | Storefront homepage -> hero banner, countdown timer, product carousel, testimonials, trust badges, newsletter |
| Customer accounts | Log in as alice@example.com -> account page shows addresses, wishlist items, order history |
| Discount codes | WELCOME10 (10% off), SUMMER25 (25%), FLAT20 ($20 off), AUDIO15 (15% audio), BIGSPEND50 ($50 off) |

## Verification Checklist

### Full Platform Verification

Run these commands to verify the platform is in a healthy state:

```bash
# 1. Backend tests (580 should pass)
cd /workspaces/ecomm/dropshipping/backend && python -m pytest tests/ -x

# 2. Dashboard build (should compile cleanly)
cd /workspaces/ecomm/dropshipping/dashboard && npm run build

# 3. Storefront build (should compile cleanly)
cd /workspaces/ecomm/dropshipping/storefront && npm run build

# 4. E2E tests (200+ should pass, requires all services running)
cd /workspaces/ecomm/e2e && npx playwright test --reporter=line
```

### Phase 2 Polish Feature Verification

Specific areas to verify after Phase 2 Polish changes:

| Feature | How to verify |
|---------|--------------|
| Platform Home KPIs | Login -> Dashboard home shows "Your Stores" with aggregate metrics |
| Store Overview KPIs | Navigate to store overview -> see revenue, orders, products cards |
| Order Notes | Open order detail -> "Internal Notes" textarea -> type and blur -> reload and verify |
| CSV Export | Orders page + Products page -> "Export CSV" button visible |
| Command Palette | Press `Ctrl+K` -> search input appears -> type to filter -> press Escape to close |
| Inventory Alerts | Create product with stock < 5 -> store overview shows "Low Stock" alert |
| Theme Engine | Themes page -> select preset -> customize blocks, colors, typography -> storefront reflects changes |
| Animations | Browse storefront -> product grids animate in with stagger -> product detail slides in |
| Product Badges | Products created recently show "New" badge; products with compare_at_price show "Sale" badge |
| Recently Viewed | Visit product pages -> scroll down on product detail -> see "Recently Viewed" section |

## Known Flaky Tests

These tests may intermittently fail due to timing/environment factors:

| Test | Reason | Workaround |
|------|--------|-----------|
| `themes-email.spec.ts` > sidebar nav | Timeout loading theme list | Increase timeout or retry |
| `Command Palette > closes on Escape` | Input focus timing in full suite | Runs reliably in isolation |

## Linting

```bash
# Python — check for issues
cd /workspaces/ecomm/dropshipping/backend
ruff check .

# Python — auto-fix
ruff check --fix .

# TypeScript — dashboard
cd /workspaces/ecomm/dropshipping/dashboard
npm run lint

# TypeScript — storefront
cd /workspaces/ecomm/dropshipping/storefront
npm run lint
```

## Environment

Tests run against the same PostgreSQL and Redis instances used for development. The `conftest.py` `client` fixture connects to the FastAPI app in-process (no server needed). E2E tests connect to running services via HTTP.

All backend tests use the `dropshipping_test` PostgreSQL schema for isolation. This prevents cross-contamination with other services (TrendScout, ContentForge, etc.) that share the same database. Each service has its own `{service}_test` schema.

Environment variables are inherited from the devcontainer's `docker-compose.yml` — no additional test configuration is required.
