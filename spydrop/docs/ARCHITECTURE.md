# Architecture

> Part of [SpyDrop](README.md) documentation

This guide covers SpyDrop's technical architecture, including the tech stack, project structure, database schema, and key design decisions.

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
| Testing | pytest + pytest-asyncio + httpx | 156 backend unit/integration tests |

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

## Database Schema

### Users & Auth Tables

| Table | Key Columns | Purpose |
|-------|------------|---------|
| `users` | id (PK), email (unique), hashed_password, plan, is_active | User accounts |
| `subscriptions` | id (PK), user_id (FK), stripe_subscription_id, status, current_period_end | Stripe subscription tracking |
| `api_keys` | id (PK), user_id (FK), key_hash, key_prefix, is_active | API key authentication |

### Domain Tables

| Table | Key Columns | Purpose |
|-------|------------|---------|
| `competitors` | id (PK), user_id (FK), name, url, platform, status, product_count, last_scanned | Monitored competitor stores |
| `competitor_products` | id (PK), competitor_id (FK), title, url, image_url, price, currency, price_history (JSON), status, first_seen, last_seen | Products discovered on competitor stores |
| `price_alerts` | id (PK), user_id (FK), competitor_product_id (FK nullable), competitor_id (FK nullable), alert_type, threshold, is_active, last_triggered | Monitoring rules |
| `alert_history` | id (PK), alert_id (FK), message, data (JSON), created_at | Triggered alert log |
| `scan_results` | id (PK), competitor_id (FK), new_products_count, removed_products_count, price_changes_count, scanned_at, duration_seconds | Scan execution records |
| `source_matches` | id (PK), competitor_product_id (FK), supplier, supplier_url, cost, currency, confidence_score, margin_percent | Reverse supplier matches |

### Key Relationships

- `User` → `Competitor` (one-to-many) — users own competitors
- `Competitor` → `CompetitorProduct` (one-to-many, cascade delete) — competitors have products
- `Competitor` → `ScanResult` (one-to-many, cascade delete) — scan history
- `CompetitorProduct` → `SourceMatch` (one-to-many, cascade delete) — supplier matches
- `CompetitorProduct` → `PriceAlert` (one-to-many, cascade delete) — product-specific alerts
- `Competitor` → `PriceAlert` (one-to-many, cascade delete) — competitor-wide alerts
- `PriceAlert` → `AlertHistory` (one-to-many, cascade delete) — alert trigger log

---

## Key Design Decisions

### 1. Plan Limit Enforcement at Service Layer

The `competitor_service.create_competitor()` function checks the user's plan tier against `PLAN_LIMITS` before allowing creation. This keeps business rules in the service layer rather than scattering them across API endpoints.

**Implementation:** Service functions call `check_plan_limit()` before resource creation, which queries the user's plan and compares current usage against tier limits.

### 2. Price History as JSON Column

`CompetitorProduct.price_history` is a PostgreSQL JSON column storing a list of `{date, price}` entries. This avoids a separate table for price snapshots while still allowing efficient appending during scans.

**Trade-off:** JSON columns are less efficient for complex queries, but price history is primarily read-only and displayed as-is in the UI. The simplicity outweighs the query performance cost.

### 3. Sentinel Value Pattern for Updates

The `alert_service.update_alert()` function uses Python's `...` (Ellipsis) as a sentinel to distinguish between:
- **Field not provided** (do not change) — Ellipsis sentinel
- **Explicitly clear the value** — `None`

This enables partial PATCH updates without requiring separate "unset" flags.

### 4. Mock Mode for Development

When `STRIPE_SECRET_KEY` is empty, all billing operations create subscriptions directly in the database without making Stripe API calls. This enables full development and testing without a Stripe account.

**How it works:** Billing service checks if `STRIPE_SECRET_KEY` is set. If not, it bypasses Stripe API calls and creates subscription records with mock Stripe IDs.

### 5. Cross-Service Provisioning

The `POST /auth/provision` endpoint allows the dropshipping platform to create users and API keys in SpyDrop via HTTP. This enables loose coupling between services with no shared database imports.

**Flow:**
1. Platform user clicks "Activate SpyDrop"
2. Platform backend calls `POST /provision` with user email
3. SpyDrop creates user account and API key
4. Platform stores API key for subsequent SpyDrop API calls

### 6. User Isolation by Design

All resource queries include a `user_id` filter. The API returns 404 (not 403) when a user tries to access another user's resource, preventing enumeration attacks.

**Pattern:** Every service function accepts `user_id` and includes it in the WHERE clause. If no resource is found, the API returns 404 rather than revealing that the resource exists but belongs to someone else.

### 7. Cascading Deletes

Deleting a competitor cascades through products, scan results, alerts, and source matches via SQLAlchemy relationship configuration (`cascade="all, delete-orphan"`).

**Configuration:**
```python
# In Competitor model
products = relationship("CompetitorProduct", back_populates="competitor", cascade="all, delete-orphan")
scan_results = relationship("ScanResult", back_populates="competitor", cascade="all, delete-orphan")
```

### 8. Config-Driven Dashboard

The `service.config.ts` file is the single source of truth for all branding, navigation, and billing tiers in the dashboard. The scaffold script replaces template placeholders to generate new service dashboards.

**What's configured:**
- Service name, tagline
- Primary/accent colors (OKLCH)
- Heading/body fonts
- Navigation items
- Plan tiers with pricing and limits

---

## Platform Event Webhook

Each service receives platform events from the dropshipping backend via `POST /api/v1/webhooks/platform-events`. Events are HMAC-SHA256 signed using `platform_webhook_secret`. The receiver verifies the signature and routes events to service-specific handlers.

**Event Types:**
- `user.created` — New user registered on platform (provision SpyDrop account)
- `user.deleted` — User deleted on platform (cascade delete SpyDrop data)
- `subscription.updated` — Plan tier changed on platform (sync to SpyDrop)

**Signature Verification:**
```python
# Verify HMAC-SHA256 signature in X-Platform-Signature header
expected_signature = hmac.new(
    secret.encode(),
    body.encode(),
    hashlib.sha256
).hexdigest()
```

---

## Design System

| Element | Value | Purpose |
|---------|-------|---------|
| Primary Color | Slate Cyan — `oklch(0.60 0.15 220)` / `#06b6d4` (Tailwind cyan-500) | Main UI accent, buttons, links |
| Accent Color | Light Cyan — `oklch(0.70 0.12 210)` / `#67e8f9` (Tailwind cyan-300) | Hover states, highlights |
| Heading Font | Geist | Clean, technical, monospaced-feeling sans-serif |
| Body Font | Geist | Matching body font for cohesive terminal-like aesthetic |
| Motion Library | framer-motion | PageTransition, FadeIn, StaggerChildren, AnimatedCounter |
| Component Library | Shadcn/ui | Card, Button, Badge, Dialog, Input, Skeleton |
| Icons | lucide-react | Consistent icon set |

**Color Philosophy:** Slate cyan evokes technical precision and competitive analysis (like terminal UIs and debugging tools). The color choice differentiates SpyDrop from competitors using purple gradients.

**Typography:** Geist provides a modern, clean aesthetic that feels intentional and distinct from generic system fonts or overused choices like Inter/Roboto.

---

*See also: [Setup](SETUP.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md) · [README](README.md)*
