# Developer Guide

## Project Overview

**For Developers:**
This guide covers the full technical architecture, local setup, project structure, conventions, and contribution patterns for the Dropshipping Platform.

The Dropshipping Platform is a multi-tenant SaaS application that lets users create and manage automated dropshipping stores. It lives in `dropshipping/` within the monorepo and integrates with 8 standalone SaaS services via the **ServiceBridge** event system. It consists of three applications:

- **Backend** — FastAPI REST API (Python 3.12) with 36 API routers, 22 models, 30 services, ~37 DB tables
- **Dashboard** — Admin interface for store owners (Next.js 16 + Shadcn/ui) with 34 pages
- **Storefront** — Customer-facing store (Next.js 16 + Tailwind) with 18 pages, 13 block types, 11 preset themes

The ServiceBridge dispatches platform lifecycle events (product created, order shipped, etc.) to connected SaaS services (ContentForge, RankPilot, FlowSend, SpyDrop, TrendScout, PostPilot, AdScale, ShopChat) via HMAC-signed HTTP webhooks through Celery background tasks.

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend framework | FastAPI | 0.115+ |
| ORM | SQLAlchemy (async) | 2.0+ |
| Database | PostgreSQL | 16 |
| Migrations | Alembic (async) | 1.14+ |
| Task queue | Celery + Redis | 5.4+ |
| Auth | python-jose (JWT) + bcrypt | — |
| Billing | Stripe (mock mode supported) | — |
| Frontend framework | Next.js (App Router) | 16 |
| UI components | Shadcn/ui (dashboard only) | — |
| Styling | Tailwind CSS | 4 |
| Animation | Motion (framer-motion) | 12.33+ |
| Charts | Recharts | 2.x |
| Language | TypeScript | 5+ |
| E2E testing | Playwright | latest |
| Backend testing | pytest + httpx | 8.3+ |

## Local Development Setup

### Prerequisites

- VS Code with the Dev Containers extension
- Docker Desktop running

### Starting the Environment

1. Open the project root in VS Code
2. Command Palette → **Dev Containers: Reopen in Container**
3. The container installs Python and Node dependencies automatically via `postCreateCommand`

### Services

All services run in the devcontainer. Open a separate terminal for each:

```bash
# Backend API — http://localhost:8000
cd /workspaces/ecomm/dropshipping/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Dashboard — http://localhost:3000
cd /workspaces/ecomm/dropshipping/dashboard
npm run dev

# Storefront — http://localhost:3001
cd /workspaces/ecomm/dropshipping/storefront
npm run dev -- -p 3001

# Celery worker
cd /workspaces/ecomm/dropshipping/backend
celery -A app.tasks.celery_app worker --loglevel=info

# Celery Beat (scheduler)
cd /workspaces/ecomm/dropshipping/backend
celery -A app.tasks.celery_app beat --loglevel=info

# Flower (task monitor, optional) — http://localhost:5555
cd /workspaces/ecomm/dropshipping/backend
celery -A app.tasks.celery_app flower --port=5555
```

### Seed Data

Populate the database with a complete demo dataset for the Volt Electronics store:

```bash
cd /workspaces/ecomm
npx tsx scripts/seed.ts
```

The seed script is **idempotent** — it checks for existing records before creating new ones, so you can safely re-run it.

**Prerequisites:** The backend must be running on port 8000 with migrations applied (`alembic upgrade head`).

**What it creates:**

| Data | Count | Details |
|------|-------|---------|
| User account | 1 | `demo@example.com` / `password123` |
| Store | 1 | "Volt Electronics" (slug: `volt-electronics`) |
| Categories | 6 | 4 top-level + 2 sub-categories |
| Products | 12 | Rich descriptions, Unsplash images, 2-4 variants each, SEO metadata |
| Suppliers | 3 | Linked to all 12 products with cost data |
| Discount codes | 5 | Mix of percentage & fixed-amount (WELCOME10, SUMMER25, FLAT20, AUDIO15, BIGSPEND50) |
| Tax rates | 4 | CA, NY, TX sales tax + UK VAT |
| Gift cards | 3 | $25, $50, $100 |
| Customer accounts | 3 | alice/bob/carol@example.com (all `password123`) with addresses and wishlists |
| Orders | 4 | Full lifecycle: pending → paid → shipped → delivered |
| Refund | 1 | Partial refund on Carol's order |
| Reviews | 14 | Across 8 products, 3-5 star ratings |
| Segments | 3 | High-Value, Repeat Buyers, VIP Early Access |
| Upsell rules | 6 | Cross-sell, upsell, and bundle recommendations |
| Team invites | 2 | marketing@ (editor) + support@ (viewer) |
| Webhooks | 2 | Order events + inventory events |
| A/B tests | 2 | Checkout button color + product page layout |
| Custom domain | 1 | shop.voltelectronics.com |
| Order notes | 4 | Internal memos on all orders |
| Theme | 1 | Cyberpunk preset activated with 8 custom blocks |

**Demo-specific features to verify after seeding:**
- **Sale badges** — 4 products have `compare_at_price` set (ProBook, Galaxy Nova, SoundStage, FlexiDock, NovaBand, MagFloat)
- **Inventory alerts** — 3 products have low stock (NovaBand: 2-4 units, MagFloat: 2-4 units)
- **Theme blocks** — Cyberpunk theme with hero, countdown timer, featured products, carousel, categories, testimonials, trust badges, newsletter

### Demo Credentials

| Role | Email | Password | Access |
|------|-------|----------|--------|
| **Store Owner** | `demo@example.com` | `password123` | Dashboard at `http://localhost:3000` |
| **Customer (Alice)** | `alice@example.com` | `password123` | Storefront at `http://localhost:3001?store=volt-electronics` |
| **Customer (Bob)** | `bob@example.com` | `password123` | Storefront at `http://localhost:3001?store=volt-electronics` |
| **Customer (Carol)** | `carol@example.com` | `password123` | Storefront at `http://localhost:3001?store=volt-electronics` |

### Ports

| Port | Service |
|------|---------|
| 8000 | Backend API |
| 3000 | Dashboard |
| 3001 | Storefront |
| 5432 | PostgreSQL |
| 6379 | Redis |
| 5555 | Flower |

### Environment Variables

Pre-configured in `.devcontainer/docker-compose.yml`:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | `postgresql+asyncpg://dropship:dropship_dev@db:5432/dropshipping` |
| `DATABASE_URL_SYNC` | `postgresql://dropship:dropship_dev@db:5432/dropshipping` |
| `REDIS_URL` | `redis://redis:6379/0` |
| `CELERY_BROKER_URL` | `redis://redis:6379/1` |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/2` |

## Project Structure

```
dropshipping/backend/
├── app/
│   ├── main.py              # FastAPI app + 36 router registrations
│   ├── config.py            # pydantic-settings (reads env vars)
│   ├── database.py          # Async engine, session factory, Base
│   ├── api/                 # FastAPI routers (36 files)
│   │   ├── health.py        # GET /api/v1/health
│   │   ├── auth.py          # Auth endpoints (register, login, refresh, me)
│   │   ├── deps.py          # Shared dependencies (get_current_user, plan limits)
│   │   ├── public.py        # Public storefront API (no auth)
│   │   ├── stores.py        # Store CRUD
│   │   ├── products.py      # Product CRUD + image upload
│   │   ├── orders.py        # Order management + fulfillment
│   │   ├── categories.py    # Category management
│   │   ├── discounts.py     # Discount codes + coupons
│   │   ├── themes.py        # Theme CRUD + presets
│   │   ├── analytics.py     # Revenue, orders, product analytics
│   │   ├── reviews.py       # Product reviews + moderation
│   │   ├── webhooks.py      # Stripe webhook handler
│   │   ├── exports.py       # CSV export (orders, products, customers)
│   │   ├── customer_auth.py # Customer login/register (storefront)
│   │   ├── customer_orders.py    # Customer order history
│   │   ├── customer_addresses.py # Customer address book
│   │   ├── customer_wishlist.py  # Customer wishlists
│   │   ├── bridge.py        # ServiceBridge REST API (5 endpoints)
│   │   └── ... (17+ more feature routers)
│   ├── models/              # SQLAlchemy models (22 files, ~37 tables)
│   │   ├── user.py          # User + plan tracking
│   │   ├── store.py         # Store + soft-delete
│   │   ├── product.py       # Product + ProductVariant
│   │   ├── order.py         # Order + OrderItem + tracking + notes
│   │   ├── customer.py      # Customer accounts + addresses
│   │   ├── theme.py         # StoreTheme (block config, typography, colors)
│   │   ├── bridge_delivery.py # BridgeDelivery ORM model (event dispatch log)
│   │   └── ... (15 more: subscription, discount, category, review, etc.)
│   ├── schemas/             # Pydantic request/response schemas (27 files)
│   │   ├── bridge.py        # ServiceBridge schemas
│   │   └── ...
│   ├── services/            # Business logic (30 files)
│   │   ├── auth_service.py  # JWT, password hashing, user CRUD
│   │   ├── store_service.py # Store CRUD + slug management
│   │   ├── product_service.py  # Product CRUD + variants + search
│   │   ├── order_service.py    # Checkout, fulfillment, status transitions
│   │   ├── theme_service.py    # Theme CRUD + preset seeding
│   │   ├── analytics_service.py # Revenue/order/product analytics queries
│   │   ├── export_service.py   # CSV generation (streaming)
│   │   ├── stripe_service.py   # Stripe Checkout + webhooks (mock mode)
│   │   ├── customer_service.py # Customer auth + account management
│   │   ├── bridge_service.py   # HMAC signing, async query helpers
│   │   └── ... (20 more service files)
│   ├── constants/
│   │   └── themes.py        # Block types (13), preset themes (11), typography
│   ├── tasks/               # Celery tasks (7 modules, 21 tasks)
│   │   ├── celery_app.py    # Celery instance + config
│   │   ├── bridge_tasks.py  # ServiceBridge event dispatch with HMAC
│   │   ├── email_tasks.py   # 9 transactional email tasks
│   │   ├── webhook_tasks.py # Store webhook delivery
│   │   ├── notification_tasks.py # Dashboard notifications
│   │   ├── fraud_tasks.py   # Fraud risk scoring
│   │   ├── order_tasks.py   # Order orchestration + auto-fulfill
│   │   └── analytics_tasks.py # Daily analytics + cleanup
│   └── utils/
│       └── slug.py          # slugify() + generate_unique_slug(exclude_id=)
├── alembic/
│   ├── env.py               # Async migration environment
│   └── versions/            # 13 migration files
├── tests/                   # ~35 test files, 580 tests
│   ├── conftest.py          # AsyncClient fixture + DB cleanup (terminates connections)
│   ├── test_auth.py         # 15 tests: register, login, refresh, me, forgot-password
│   ├── test_stores.py       # 20 tests: CRUD, slugs, tenant isolation, soft-delete
│   ├── test_products.py     # 24 tests: CRUD, variants, search, pagination, images
│   ├── test_orders.py       # 21+ tests: checkout, fulfillment, status, notes
│   ├── test_themes.py       # Theme CRUD, presets, block config
│   ├── test_reviews.py      # Review CRUD, moderation, ratings
│   ├── test_customers.py    # Customer auth, addresses, wishlist
│   ├── test_refunds.py      # Refund processing
│   ├── test_bridge_api.py   # ServiceBridge API endpoint tests
│   ├── test_bridge_service.py # ServiceBridge service layer tests
│   ├── test_bridge_tasks.py # ServiceBridge Celery task tests
│   └── ... (22+ more test files)
└── pyproject.toml           # Dependencies + pytest/ruff config

dropshipping/dashboard/
├── src/
│   ├── app/                 # App Router pages (34 pages)
│   │   ├── layout.tsx       # Root layout (custom fonts + AuthProvider)
│   │   ├── page.tsx         # Platform home (aggregate KPIs, store cards)
│   │   ├── globals.css      # OKLCH design system (teal/amber)
│   │   ├── (auth)/          # Auth route group
│   │   │   ├── login/       # Login page
│   │   │   └── register/    # Registration page
│   │   ├── stores/
│   │   │   ├── page.tsx     # Store list
│   │   │   ├── new/         # Create store
│   │   │   └── [id]/        # Store-scoped pages (28 sub-pages)
│   │   │       ├── page.tsx        # Store overview (KPI dashboard)
│   │   │       ├── products/       # Product list, create, edit
│   │   │       ├── orders/         # Order list + detail (with fulfillment + notes)
│   │   │       ├── analytics/      # Revenue, orders, product performance
│   │   │       ├── themes/         # Theme list + full config editor
│   │   │       ├── categories/     # Category management
│   │   │       ├── discounts/      # Discount codes
│   │   │       ├── reviews/        # Review moderation
│   │   │       ├── gift-cards/     # Gift card management
│   │   │       ├── services/
│   │   │       │   └── activity/   # ServiceBridge activity log with KPIs
│   │   │       └── ... (14+ more feature pages)
│   │   ├── billing/         # Subscription management
│   │   ├── pricing/         # Plan comparison
│   │   └── notifications/   # Notification center
│   ├── components/
│   │   ├── dashboard-shell.tsx      # Shell wrapper (sidebar + top bar + Cmd+K)
│   │   ├── sidebar.tsx              # Collapsible sidebar (platform/store modes)
│   │   ├── top-bar.tsx              # Top navigation bar
│   │   ├── command-palette.tsx      # Cmd+K command palette (fuzzy search, navigation)
│   │   ├── inventory-alerts.tsx     # Low-stock warning cards
│   │   ├── motion-wrappers.tsx      # FadeIn, StaggerChildren animation wrappers
│   │   ├── authenticated-layout.tsx # Auth guard HOC
│   │   ├── service-activity-card.tsx   # ServiceBridge reusable delivery list widget
│   │   ├── resource-service-status.tsx # 8-service status grid for resources
│   │   └── ui/                      # Shadcn/ui components
│   ├── contexts/
│   │   ├── auth-context.tsx         # AuthProvider + useAuth() hook
│   │   └── store-context.tsx        # StoreProvider + useStoreContext() hook
│   └── lib/
│       ├── api.ts           # API client (fetch wrapper with JWT + upload)
│       ├── auth.ts          # Token cookie helpers
│       └── utils.ts         # cn() class merge utility
├── components.json          # Shadcn/ui config
└── package.json

dropshipping/storefront/
├── src/
│   ├── app/                 # App Router pages (18 pages)
│   │   ├── layout.tsx       # Root layout (theme CSS vars, header, cart, auth)
│   │   ├── page.tsx         # Homepage (block-based, theme-driven)
│   │   ├── products/
│   │   │   ├── page.tsx     # Product listing (animated grid)
│   │   │   └── [slug]/page.tsx  # Product detail (zoom, reviews, upsells, recently viewed)
│   │   ├── categories/
│   │   │   ├── page.tsx     # Category listing
│   │   │   └── [slug]/page.tsx  # Category detail
│   │   ├── cart/page.tsx    # Shopping cart
│   │   ├── checkout/
│   │   │   ├── page.tsx     # Checkout form
│   │   │   └── success/page.tsx  # Order confirmation
│   │   ├── search/page.tsx  # Search with autocomplete
│   │   ├── account/         # Customer account (6 pages: login, register, orders, wishlist, addresses, settings)
│   │   └── policies/[slug]/ # Legal policy pages
│   ├── components/
│   │   ├── blocks/          # 13 theme block renderers
│   │   │   ├── block-renderer.tsx   # Block orchestrator
│   │   │   ├── hero-banner.tsx      # Hero with product showcase mode
│   │   │   ├── featured-products.tsx
│   │   │   ├── categories-grid.tsx
│   │   │   ├── product-carousel.tsx # Auto-scroll with snap
│   │   │   ├── testimonials.tsx     # Cards or slider layout
│   │   │   ├── countdown-timer.tsx  # Live countdown
│   │   │   ├── video-banner.tsx     # YouTube/Vimeo embed
│   │   │   ├── trust-badges.tsx     # Free shipping, secure checkout, etc.
│   │   │   ├── reviews-block.tsx
│   │   │   ├── newsletter.tsx
│   │   │   ├── custom-text.tsx
│   │   │   ├── image-banner.tsx
│   │   │   └── spacer.tsx
│   │   ├── motion-primitives.tsx    # FadeIn, StaggerChildren, SlideIn, ScaleIn, ScrollReveal
│   │   ├── animated-product-grid.tsx # Staggered grid with motion
│   │   ├── product-grid.tsx         # Base product grid
│   │   ├── add-to-cart.tsx          # Variant selector + quantity + animated button
│   │   ├── recently-viewed.tsx      # localStorage-based recently viewed products
│   │   ├── product-reviews.tsx      # Review display
│   │   ├── product-upsells.tsx      # Cross-sell recommendations
│   │   ├── header-search.tsx        # Search autocomplete in header
│   │   ├── mobile-menu.tsx          # Spring-based mobile drawer
│   │   ├── account-link.tsx         # Customer auth link
│   │   └── cart-badge.tsx           # Animated cart count badge
│   ├── contexts/
│   │   ├── cart-context.tsx         # CartProvider (localStorage persistence)
│   │   ├── auth-context.tsx         # Customer auth context
│   │   └── store-context.tsx        # Store data context
│   └── lib/
│       ├── api.ts           # Public API client
│       ├── auth.ts          # Customer token management
│       ├── types.ts         # TypeScript interfaces
│       └── theme-utils.ts   # CSS variable generation from theme config
└── package.json

e2e/
├── tests/
│   ├── helpers.ts           # Shared utilities (registerUser, createStoreAPI, etc.)
│   ├── dashboard/           # 19 spec files
│   │   ├── auth.spec.ts
│   │   ├── stores.spec.ts
│   │   ├── orders.spec.ts
│   │   ├── fulfillment.spec.ts
│   │   ├── products.spec.ts
│   │   ├── categories.spec.ts
│   │   ├── discounts.spec.ts
│   │   ├── themes-email.spec.ts
│   │   ├── reviews-analytics.spec.ts
│   │   ├── phase2-polish.spec.ts   # KPIs, command palette, CSV export, inventory alerts
│   │   └── ... (9 more)
│   └── storefront/          # 6 spec files
│       ├── browse.spec.ts
│       ├── cart-checkout.spec.ts
│       ├── categories-search.spec.ts
│       ├── customer-accounts.spec.ts
│       └── ... (2 more)
├── playwright.config.ts
└── package.json

scripts/
└── seed.ts                  # Demo data seed (Volt Electronics)

plan/
├── ARCHITECTURE.md          # Technical architecture document
├── BACKLOG.md               # Feature backlog with acceptance criteria
└── POLISH_PLAN.md           # Phase 2 Polish implementation details
```

## Database Migrations

```bash
cd /workspaces/ecomm/dropshipping/backend

# Create a new migration after model changes
alembic revision --autogenerate -m "description of changes"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# See current migration state
alembic current

# Merge multiple heads (when parallel branches create conflicts)
alembic merge heads -m "merge heads"
```

Alembic is configured for async via `asyncpg`. The `env.py` imports `Base.metadata` from `app.database` so autogenerate detects model changes. There are currently 13 migrations managing ~37 database tables.

**Important:** When parallel feature branches create multiple Alembic heads, run `alembic merge heads -m "merge heads"` before `alembic upgrade head`.

## Testing

### Backend Tests (580 tests, ~35 files)

```bash
cd /workspaces/ecomm/dropshipping/backend

# Run all tests
python -m pytest tests/ -x

# Verbose output
pytest -v

# Specific file
pytest tests/test_orders.py

# Run with keyword filter
pytest -k "checkout"
```

Tests use `pytest-asyncio` with `asyncio_mode = "auto"`. The `client` fixture in `conftest.py` provides an `httpx.AsyncClient` wired to the FastAPI app via `ASGITransport`. A `clean_tables` autouse fixture truncates all tables between tests for isolation — it terminates **all** non-self database connections before truncating to prevent deadlocks with any running backend process.

### Test Isolation (Schema-Based)

Tests use schema-based isolation with the `dropshipping_test` PostgreSQL schema. Raw asyncpg handles schema creation and termination. The `search_path` is set via a SQLAlchemy `connect` event listener.

Key rules:
- Each service gets a `{service_name}_test` schema (e.g., `dropshipping_test`)
- Session-scoped `create_tables` fixture creates the schema once; per-test `truncate_tables` fixture cleans up
- **Never use `pg_terminate_backend` without schema filtering** — it kills other services' connections
- Any test file with its own DB engine **must** set `search_path` to the test schema

### Test Counts

| Category | Count | Details |
|----------|-------|---------|
| **Total** | 580 | All backend tests |
| **Core features** | 541 | Auth, stores, products, orders, themes, reviews, etc. |
| **ServiceBridge** | 39 | `test_bridge_api.py`, `test_bridge_service.py`, `test_bridge_tasks.py` |

### E2E Tests (200+ tests, 25 spec files)

```bash
cd /workspaces/ecomm/e2e

# Run all e2e tests (requires backend + dashboard + storefront running)
npx playwright test

# Run specific spec file
npx playwright test tests/dashboard/orders.spec.ts

# Run with line reporter for CI
npx playwright test --reporter=line

# Run headed (visible browser)
npx playwright test --headed

# Run with repeat to check flakiness
npx playwright test tests/dashboard/phase2-polish.spec.ts --repeat-each=3
```

**Prerequisites:** The backend (port 8000), dashboard (port 3000), and storefront (port 3001) must all be running before executing e2e tests.

### Writing a Backend Test

```python
# dropshipping/backend/tests/test_example.py
"""
Tests for the example feature.

**For Developers:**
  Covers CRUD operations and edge cases for the example endpoint.

**For QA Engineers:**
  Validates that example resources can be created, read, updated, and deleted
  with proper authorization checks.
"""
import pytest

@pytest.mark.asyncio
async def test_something(client):
    """Verify the example endpoint returns a 200 status with expected data."""
    response = await client.get("/api/v1/some-endpoint")
    assert response.status_code == 200
```

### Writing an E2E Test

```typescript
// e2e/tests/dashboard/example.spec.ts
import { test, expect } from "@playwright/test";
import { registerUser, dashboardLogin, createStoreAPI } from "../helpers";

test.describe("Example Feature", () => {
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

  test("does something useful", async ({ page }) => {
    await page.goto(`/stores/${storeId}/example`);
    await expect(page.getByText("Expected Content")).toBeVisible({ timeout: 10000 });
  });
});
```

**E2E test patterns:**
- Use `registerUser()` + `createStoreAPI()` + `dashboardLogin()` for setup
- Use `.first()` when multiple elements might match (Playwright strict mode)
- Use `{ exact: true }` for exact text matching
- Use `{ timeout: 10000 }` for assertions that wait for data to load

## ServiceBridge — Platform Event Integration

The ServiceBridge dispatches platform lifecycle events to connected SaaS services via HMAC-signed HTTP webhooks through Celery background tasks.

### Key Files

| File | Purpose |
|------|---------|
| `dropshipping/backend/app/tasks/bridge_tasks.py` | Celery task with `EVENT_SERVICE_MAP` |
| `dropshipping/backend/app/services/bridge_service.py` | HMAC signing, async query helpers |
| `dropshipping/backend/app/api/bridge.py` | REST API (5 endpoints) for dashboard |
| `dropshipping/backend/app/models/bridge_delivery.py` | `BridgeDelivery` ORM model |
| `dropshipping/backend/app/schemas/bridge.py` | Pydantic schemas |

### Event Dispatch Flow

1. API handler (e.g. `products.py`) calls `fire_platform_event()` after CRUD
2. `fire_platform_event()` lazy-imports and calls `dispatch_platform_event.delay()`
3. Celery task queries `ServiceIntegration` for connected services
4. Filters by `EVENT_SERVICE_MAP` (5 event types mapped to service lists)
5. POSTs to each service with HMAC-SHA256 signature header
6. Records `BridgeDelivery` row for each attempt (success/failure, latency)

### Event-Service Mapping

| Event | Services |
|-------|---------|
| `product.created` | ContentForge, RankPilot, TrendScout, PostPilot, AdScale, ShopChat |
| `product.updated` | ContentForge, RankPilot, ShopChat |
| `order.created` | FlowSend, SpyDrop |
| `order.shipped` | FlowSend |
| `customer.created` | FlowSend |

### HMAC Signing

Events are signed with `platform_webhook_secret` (shared secret in config). Services verify via `X-Platform-Signature` header using HMAC-SHA256.

### Bridge API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/bridge/activity` | GET | Paginated delivery log with filters |
| `/api/v1/bridge/activity/{type}/{id}` | GET | Per-resource deliveries |
| `/api/v1/bridge/service/{name}/activity` | GET | Per-service deliveries |
| `/api/v1/bridge/summary` | GET | 24h per-service summary |
| `/api/v1/bridge/dispatch` | POST | Manual event dispatch |

### Dashboard Components

| Component | File | Purpose |
|-----------|------|---------|
| Service Activity Card | `dropshipping/dashboard/src/components/service-activity-card.tsx` | Reusable delivery list widget |
| Resource Service Status | `dropshipping/dashboard/src/components/resource-service-status.tsx` | 8-service status grid |
| Activity Page | `dropshipping/dashboard/src/app/stores/[id]/services/activity/page.tsx` | Full activity log with KPIs |

## Background Tasks (Celery)

21 task functions across 7 modules:

| Module | Tasks | Purpose |
|--------|-------|---------|
| `bridge_tasks.py` | 1 | ServiceBridge event dispatch with HMAC |
| `email_tasks.py` | 9 | Transactional emails |
| `webhook_tasks.py` | 1 | Store webhook delivery |
| `notification_tasks.py` | 4 | Dashboard notifications |
| `fraud_tasks.py` | 1 | Fraud risk scoring |
| `order_tasks.py` | 3 | Order orchestration + auto-fulfill |
| `analytics_tasks.py` | 2 | Daily analytics + cleanup |

All task modules live in `dropshipping/backend/app/tasks/`. Celery workers use `SyncSessionFactory` (psycopg2), not asyncpg. Always pass UUIDs as strings to `.delay()`.

## Theme System Architecture

The storefront uses a powerful theme engine with 13 block types and 11 preset themes.

### Block Types

Blocks are the building units of storefront pages. Each block has a type and a JSON config:

| Block Type | Purpose |
|-----------|---------|
| `hero_banner` | Hero section with gradient, image, or product showcase backgrounds |
| `featured_products` | Grid of featured products (configurable count/columns) |
| `categories_grid` | Category browsing grid |
| `product_carousel` | Auto-scrolling product carousel with snap points |
| `testimonials` | Customer testimonials (cards or slider layout) |
| `countdown_timer` | Sale/launch countdown timer |
| `video_banner` | YouTube/Vimeo video embed with overlay |
| `trust_badges` | Trust indicators (shipping, security, guarantee) |
| `reviews` | Customer review grid |
| `newsletter` | Email subscription section |
| `custom_text` | Custom HTML/text content |
| `image_banner` | Static image with text overlay |
| `spacer` | Vertical spacing |

### Preset Themes

11 preset themes with complete color/typography/layout configurations:

| Theme | Vibe | Primary Color | Heading Font |
|-------|------|--------------|-------------|
| Frosted (default) | Clean, modern | Teal | Bricolage Grotesque |
| Midnight | Dark, sleek | Cyan | Syne |
| Botanical | Organic, natural | Forest Green | Fraunces |
| Neon | Electric, bold | Hot Pink | Unbounded |
| Luxe | Premium, elegant | Gold | Playfair Display |
| Playful | Fun, vibrant | Orange | Outfit |
| Industrial | Raw, utilitarian | Charcoal | Archivo Black |
| Coastal | Airy, beach | Ocean Blue | Josefin Sans |
| Monochrome | Minimal, editorial | Black | DM Serif Display |
| Cyberpunk | Futuristic, neon | Electric Purple | Unbounded |
| Terracotta | Earthy, warm | Terracotta | Bitter |

### Theme CSS Variables

Themes generate CSS variables via `dropshipping/storefront/src/lib/theme-utils.ts`:

```css
--theme-primary, --theme-accent, --theme-background, --theme-foreground
--theme-heading-font, --theme-body-font, --theme-mono-font
--theme-heading-weight, --theme-body-weight
--theme-letter-spacing, --theme-line-height
--theme-border-radius, --theme-card-style, --theme-button-style
```

## Animation System

The storefront uses `motion` (framer-motion) for animations via reusable primitives in `dropshipping/storefront/src/components/motion-primitives.tsx`:

| Primitive | Effect |
|-----------|--------|
| `FadeIn` | Opacity 0→1 + translateY(20px→0) |
| `StaggerChildren` | Wraps children with staggered delays (50-80ms) |
| `SlideIn` | Slide from configurable direction |
| `ScaleIn` | Scale 0.95→1 with opacity |
| `ScrollReveal` | Triggers animation on viewport entry (IntersectionObserver) |

**Applied to:** Product grids, product detail pages, cart, checkout success, category pages, mobile menu. Dashboard uses `motion-wrappers.tsx` for staggered card entrances and animated counters.

## Code Quality

- **Python**: Ruff (configured in `pyproject.toml`, line-length=100, target py312)
- **TypeScript**: ESLint + Prettier (auto-format on save in VS Code)

## API Conventions

- All endpoints prefixed with `/api/v1/`
- Auth header: `Authorization: Bearer <jwt>`
- Paginated response: `{ "items": [...], "total": N, "page": N, "per_page": N }`
- Store-scoped routes: `/api/v1/stores/{store_id}/products`
- Public routes (no auth): `/api/v1/public/stores/{slug}/...`
- Customer auth routes: `/api/v1/customer/...` (customer JWT, not store-owner JWT)
- Export routes: `/api/v1/stores/{store_id}/orders/export?format=csv`
- Bridge routes: `/api/v1/bridge/...` (ServiceBridge activity and dispatch)
- Auto-generated docs: Swagger UI at `/docs`, ReDoc at `/redoc`

### Key API Patterns

- **Slug uniqueness:** Use `generate_unique_slug(exclude_id=)` when updating resources to avoid self-collision
- **Sentinel values:** Use Python `...` (Ellipsis) as sentinel to distinguish "not provided" from `None` in update functions
- **Soft-delete:** Stores use status-based soft-delete (status=deleted), not hard delete
- **Customer vs Owner auth:** Store owners use `get_current_user` dependency; customers use `get_current_customer` with separate JWT tokens

## Key Design Decisions

1. **Multi-tenant isolation:** All store-scoped queries filter by `store_id` + owner `user_id`. Tenant isolation is enforced at the service layer.
2. **Mock Stripe:** When `STRIPE_SECRET_KEY` is not configured, Stripe operations return mock responses. This enables full local development without a Stripe account.
3. **Block-based themes:** Storefront pages are composed of configurable blocks (not hardcoded layouts). The theme editor in the dashboard allows full block config editing.
4. **CSS variable theming:** All theme values (colors, fonts, spacing, border-radius) are applied via CSS custom properties, enabling runtime theme switching.
5. **Customer accounts:** Separate from store-owner accounts. Customers register per-store with their own JWT tokens, can manage addresses, wishlists, and order history.
6. **ServiceBridge async event dispatch:** Platform events (product CRUD, order lifecycle, customer creation) are dispatched asynchronously via Celery tasks to avoid blocking API responses. Each dispatch is signed with HMAC-SHA256 and logged as a `BridgeDelivery` record for auditability and retry visibility.
