# Developer Guide

**For Developers:** SpyDrop is a Competitor Intelligence SaaS service that monitors competitor stores, tracks product catalogs and price changes, sends configurable alerts on significant changes, and performs reverse source-finding to identify original suppliers. It can operate standalone or integrate with the dropshipping platform via HTTP API provisioning.

---

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Backend API | FastAPI + SQLAlchemy 2.0 (async) | Async throughout, Pydantic v2 schemas |
| Database | PostgreSQL 16 | UUID primary keys, JSON columns for price history |
| Cache / Queue | Redis 7 | Session cache, Celery broker and result backend |
| Task Queue | Celery | Background scans, alert evaluation, source matching |
| Scraping Engine | Playwright (headless) | Platform-aware scraping (Shopify, WooCommerce, custom) |
| Dashboard | Next.js 16 (App Router) | React 19, Shadcn/ui component library |
| Styling | Tailwind CSS | OKLCH color variables, Geist font family |
| Landing Page | Next.js 16 (static export) | Marketing and pricing page |
| Auth | JWT (python-jose) + bcrypt | Access tokens (15min) + refresh tokens (7 days) |
| Billing | Stripe (with mock mode) | Checkout sessions, webhooks, customer portal |
| Migrations | Alembic | Async-compatible with SQLAlchemy 2.0 |
| Testing | pytest + pytest-asyncio + httpx | 43 backend unit/integration tests |

---

## Local Dev Setup

### Prerequisites
- Python 3.12+
- Node.js 20+
- PostgreSQL 16
- Redis 7
- Docker + Docker Compose (recommended)

### Quick Start

```bash
# From /workspaces/ecomm/spydrop/
make install     # Install Python + Node dependencies
make migrate     # Run Alembic migrations
make start       # Start all services (backend, dashboard, landing)
```

### Access Points

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8105 |
| API Docs (Swagger) | http://localhost:8105/docs |
| Dashboard | http://localhost:3105 |
| Landing Page | http://localhost:3205 |

---

## Ports

| Port | Service | Protocol |
|------|---------|----------|
| 8105 | Backend API (FastAPI) | HTTP |
| 3105 | Dashboard (Next.js) | HTTP |
| 3205 | Landing Page (Next.js static) | HTTP |
| 5505 | PostgreSQL 16 | TCP |
| 6405 | Redis 7 | TCP |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...@db:5505/spydrop` | Async PostgreSQL connection |
| `DATABASE_URL_SYNC` | `postgresql://...@db:5505/spydrop` | Sync connection for Alembic |
| `REDIS_URL` | `redis://redis:6405/0` | Redis cache |
| `CELERY_BROKER_URL` | `redis://redis:6405/1` | Celery task broker |
| `CELERY_RESULT_BACKEND` | `redis://redis:6405/2` | Celery result storage |
| `JWT_SECRET_KEY` | (required) | Secret for signing JWT tokens |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token TTL |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |
| `STRIPE_SECRET_KEY` | (empty = mock mode) | Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | (empty = mock mode) | Stripe webhook signature secret |
| `STRIPE_BILLING_SUCCESS_URL` | `http://localhost:3105/billing` | Checkout success redirect |
| `STRIPE_BILLING_CANCEL_URL` | `http://localhost:3105/billing` | Checkout cancel redirect |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8105` | Dashboard -> backend URL |

---

## Project Structure

```
spydrop/
+-- Makefile                       # Build/test/run targets
+-- README.md                      # Service overview
+-- docker-compose.yml             # Local dev containers
+-- docs/                          # Documentation (this directory)
+-- scripts/                       # Utility scripts
+-- backend/
|   +-- app/
|   |   +-- main.py                # FastAPI application entry point
|   |   +-- config.py              # Pydantic settings
|   |   +-- database.py            # Async engine + session factory
|   |   +-- api/
|   |   |   +-- __init__.py        # Router registration
|   |   |   +-- auth.py            # POST /auth/register, /login, /refresh, /me, /provision
|   |   |   +-- competitors.py     # CRUD /competitors + /competitors/{id}/products
|   |   |   +-- products.py        # GET /products (cross-competitor), GET /products/{id}
|   |   |   +-- billing.py         # Plans, checkout, portal, subscription, overview
|   |   |   +-- api_keys.py        # Create, list, revoke API keys
|   |   |   +-- usage.py           # GET /usage (cross-service integration)
|   |   |   +-- webhooks.py        # POST /webhooks/stripe
|   |   |   +-- health.py          # GET /health
|   |   |   +-- deps.py            # Dependency injection (auth, plan limits)
|   |   +-- models/
|   |   |   +-- base.py            # SQLAlchemy DeclarativeBase
|   |   |   +-- user.py            # User model + PlanTier enum
|   |   |   +-- subscription.py    # Subscription model + SubscriptionStatus enum
|   |   |   +-- api_key.py         # ApiKey model (SHA-256 hashed)
|   |   |   +-- competitor.py      # Competitor + CompetitorProduct models
|   |   |   +-- alert.py           # PriceAlert + AlertHistory models
|   |   |   +-- scan.py            # ScanResult model
|   |   |   +-- source_match.py    # SourceMatch model
|   |   +-- schemas/
|   |   |   +-- auth.py            # Auth request/response schemas
|   |   |   +-- competitor.py      # Competitor/product schemas
|   |   |   +-- billing.py         # Billing/subscription schemas
|   |   +-- services/
|   |   |   +-- auth_service.py    # Registration, login, JWT, API key auth, provisioning
|   |   |   +-- competitor_service.py  # Competitor CRUD + plan limit checks
|   |   |   +-- scan_service.py    # Store scanning (mock), product diff detection
|   |   |   +-- alert_service.py   # Alert CRUD + scan-based triggering
|   |   |   +-- source_service.py  # Reverse source matching (mock suppliers)
|   |   |   +-- billing_service.py # Stripe checkout, portal, webhook sync, usage
|   |   +-- constants/
|   |   |   +-- plans.py           # Plan tier limits (free/pro/enterprise)
|   |   +-- tasks/                 # Celery task definitions
|   |   +-- utils/                 # Shared utilities
|   +-- tests/
|   |   +-- conftest.py            # Fixtures: client, db, auth_headers, register_and_login
|   |   +-- test_auth.py           # 11 auth tests
|   |   +-- test_competitors.py    # 17 competitor tests
|   |   +-- test_products.py       # 12 product tests
|   |   +-- test_billing.py        # 9 billing tests
|   |   +-- test_api_keys.py       # 5 API key tests
|   |   +-- test_health.py         # 1 health test
|   +-- alembic/                   # Database migrations
+-- dashboard/
|   +-- src/
|   |   +-- service.config.ts      # Branding, navigation, plans (single source of truth)
|   |   +-- app/
|   |   |   +-- page.tsx           # Dashboard home (KPI cards, quick actions)
|   |   |   +-- competitors/page.tsx  # Competitor table + add/delete dialogs
|   |   |   +-- products/page.tsx  # Product grid with filters, sort, price history
|   |   |   +-- billing/page.tsx   # Plan cards, checkout, subscription management
|   |   |   +-- api-keys/page.tsx  # API key management
|   |   |   +-- settings/page.tsx  # User settings
|   |   |   +-- login/page.tsx     # Login form
|   |   |   +-- register/page.tsx  # Registration form
|   |   +-- components/            # Shared UI components (Shell, motion, ui/)
|   |   +-- lib/                   # API client, auth utilities
+-- landing/                       # Static marketing site
```

---

## Database Migrations

```bash
# Create a new migration
cd backend && alembic revision --autogenerate -m "description"

# Apply all migrations
make migrate
# or: cd backend && alembic upgrade head

# Check current migration state
cd backend && alembic current

# Merge multiple heads (if parallel development creates branches)
cd backend && alembic merge heads -m "merge heads"
```

---

## Testing

SpyDrop has **43 backend tests** covering all API endpoints and service logic.

```bash
# Run all tests
make test-backend

# Run with verbose output
cd backend && pytest -v

# Run a specific test file
cd backend && pytest tests/test_competitors.py -v

# Run a single test
cd backend && pytest tests/test_competitors.py::test_create_competitor_success -v
```

### Test Architecture

- **Framework:** pytest + pytest-asyncio + httpx `AsyncClient`
- **Database:** Uses the same PostgreSQL database with `NullPool` for isolation
- **Cleanup:** Tables are truncated with `CASCADE` between tests; non-self DB connections are terminated to prevent deadlocks
- **Auth Helper:** `register_and_login(client, email)` creates a user and returns JWT `Authorization` headers
- **Stripe Mode:** All tests run in mock mode (empty `STRIPE_SECRET_KEY`), so subscriptions are created directly without Stripe API calls

### Test Coverage by Module

| Module | Tests | Coverage Areas |
|--------|-------|----------------|
| `test_auth.py` | 11 | Register, login, refresh, profile, duplicate email, wrong password, short password |
| `test_competitors.py` | 17 | CRUD, plan limits (free=3), pagination, user isolation, invalid IDs, partial updates |
| `test_products.py` | 12 | Cross-competitor listing, status filter, sort by price/date/title, price history, user isolation |
| `test_billing.py` | 9 | Plans listing, checkout (pro/free/duplicate), overview, subscription state |
| `test_api_keys.py` | 5 | Create, list, revoke, X-API-Key auth, invalid key |
| `test_health.py` | 1 | Health check returns 200 with service metadata |

---

## API Conventions

- **Base path:** `/api/v1/`
- **Authentication:** `Authorization: Bearer <JWT>` or `X-API-Key: <key>` header
- **Pagination:** `?page=1&per_page=20` (1-based, max 100 per page)
- **Response format:** Paginated lists use `{ items: [...], total: N, page: N, per_page: N }`
- **Error format:** `{ "detail": "error message" }`
- **Status codes:**
  - `200` — Success
  - `201` — Created
  - `204` — Deleted (no body)
  - `400` — Bad request / invalid input
  - `401` — Unauthenticated
  - `403` — Plan limit exceeded
  - `404` — Not found (also used for authorization failures to prevent enumeration)
  - `409` — Conflict (duplicate email)
  - `422` — Validation error (Pydantic)
- **IDs:** UUID v4 strings
- **Timestamps:** ISO 8601 format

---

## Design System

| Element | Value |
|---------|-------|
| Primary Color | Slate Cyan -- `oklch(0.60 0.15 220)` / `#06b6d4` (Tailwind cyan-500) |
| Accent Color | Light Cyan -- `oklch(0.70 0.12 210)` / `#67e8f9` (Tailwind cyan-300) |
| Heading Font | Geist (clean, technical, monospaced-feeling sans-serif) |
| Body Font | Geist (matching body font for cohesive terminal-like aesthetic) |
| Motion | PageTransition, FadeIn, StaggerChildren, AnimatedCounter |
| Component Library | Shadcn/ui (Card, Button, Badge, Dialog, Input, Skeleton) |
| Icons | lucide-react |

The dashboard is config-driven via `dashboard/src/service.config.ts` which defines the service name, tagline, colors, fonts, navigation items, and plan tiers. Changing this file updates the entire dashboard branding.

---

## Key Design Decisions

1. **Plan limit enforcement at service layer:** The `competitor_service.create_competitor()` function checks the user's plan tier against `PLAN_LIMITS` before allowing creation. This keeps business rules in the service layer rather than scattering them across API endpoints.

2. **Price history as JSON column:** `CompetitorProduct.price_history` is a PostgreSQL JSON column storing a list of `{date, price}` entries. This avoids a separate table for price snapshots while still allowing efficient appending during scans.

3. **Sentinel value pattern for updates:** The `alert_service.update_alert()` function uses Python's `...` (Ellipsis) as a sentinel to distinguish between "field not provided" (do not change) and `None` (explicitly clear the value). This enables partial PATCH updates.

4. **Mock mode for development:** When `STRIPE_SECRET_KEY` is empty, all billing operations create subscriptions directly in the database without making Stripe API calls. This enables full development and testing without a Stripe account.

5. **Cross-service provisioning:** The `POST /auth/provision` endpoint allows the dropshipping platform to create users and API keys in SpyDrop via HTTP. This enables loose coupling between services with no shared database imports.

6. **User isolation by design:** All resource queries include a `user_id` filter. The API returns 404 (not 403) when a user tries to access another user's resource, preventing enumeration attacks.

7. **Cascading deletes:** Deleting a competitor cascades through products, scan results, alerts, and source matches via SQLAlchemy relationship configuration (`cascade="all, delete-orphan"`).

8. **Config-driven dashboard:** The `service.config.ts` file is the single source of truth for all branding, navigation, and billing tiers in the dashboard. The scaffold script replaces template placeholders to generate new service dashboards.

---

## Platform Event Webhook

### Platform Event Webhook

Each service receives platform events from the dropshipping backend via
`POST /api/v1/webhooks/platform-events`. Events are HMAC-SHA256 signed
using `platform_webhook_secret`. The receiver verifies the signature and
routes events to service-specific handlers.
