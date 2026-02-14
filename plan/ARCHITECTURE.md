# Architecture & Stack Decisions

## Decisions Made

| Decision          | Choice                          | Rationale                                              |
| ----------------- | ------------------------------- | ------------------------------------------------------ |
| Backend language  | Python 3.12+ / FastAPI          | Developer expertise, strong AI/scraping ecosystem      |
| Frontend          | Next.js 16 (App Router)         | SEO, component ecosystem (Shadcn/ui), industry standard|
| Database          | PostgreSQL 16 + SQLAlchemy 2.0  | Async ORM, Alembic migrations, row-level security      |
| Cache / Broker    | Redis                           | Caching, sessions, Celery broker — single dependency   |
| Task queue        | Celery + Celery Beat + Flower   | Battle-tested, chains/groups for workflows, scheduling |
| Auth              | Custom JWT (python-jose)        | Full control, no cost, no vendor lock-in               |
| Payments          | Stripe (subscriptions + checkout)| Industry standard, Python SDK                         |
| Deployment        | Kubernetes from day 1           | Production-grade, existing cluster available            |
| Store multi-tenancy| Single Next.js app + subdomain routing | One deployment, cheaper, data-driven per request |
| AI                | Claude API (anthropic SDK)      | Primary LLM for product analysis, content generation   |
| File storage      | S3 / Cloudflare R2              | Images, assets, via boto3                              |
| SaaS services      | 8 standalone FastAPI services   | Each independently hostable; shared code via packages/py-core |
| ServiceBridge      | HMAC-signed Celery webhooks     | Platform events auto-dispatched to connected services         |
| LLM Gateway        | Centralized AI routing          | Single API key management point for all AI providers          |

---

## Project Structure (Phase 3 Monorepo)

```
ecomm/
├── dropshipping/                # Core dropshipping platform
│   ├── backend/                 # Python (FastAPI) — port 8000
│   │   ├── app/
│   │   │   ├── main.py          # FastAPI app entry point
│   │   │   ├── config.py        # Settings (pydantic-settings)
│   │   │   ├── database.py      # SQLAlchemy engine + session
│   │   │   ├── models/          # 20+ SQLAlchemy models
│   │   │   ├── schemas/         # Pydantic request/response schemas
│   │   │   ├── api/             # FastAPI routers (30+ endpoints)
│   │   │   │   ├── bridge.py    # ServiceBridge activity/dispatch API
│   │   │   │   ├── products.py  # fires platform events on CRUD
│   │   │   │   ├── orders.py    # fires order.shipped events
│   │   │   │   └── ...
│   │   │   ├── services/        # Business logic
│   │   │   │   ├── bridge_service.py  # HMAC signing, event queries
│   │   │   │   └── ...
│   │   │   ├── tasks/           # Celery tasks (21 task functions)
│   │   │   │   ├── bridge_tasks.py    # Platform event dispatch to services
│   │   │   │   ├── celery_app.py
│   │   │   │   └── ...
│   │   │   └── utils/
│   │   ├── alembic/             # Database migrations
│   │   └── tests/               # 580 tests
│   ├── dashboard/               # Next.js admin dashboard — port 3000
│   └── storefront/              # Next.js customer storefront — port 3001
│
├── packages/                    # Shared packages
│   ├── py-core/                 # ecomm_core: auth, billing, DB, models, health, testing
│   ├── py-connectors/           # ecomm_connectors: Shopify, WooCommerce adapters
│   └── ts-ui-kit/               # Shared TypeScript UI components
│
├── trendscout/                  # AI Product Research (Syne / DM Sans)
│   ├── backend/                 # port 8101 — 158 tests
│   ├── dashboard/               # port 3101
│   └── landing/                 # port 3201
├── contentforge/                # AI Content Generator (Clash Display / Satoshi)
│   ├── backend/                 # port 8102 — 116 tests
│   ├── dashboard/               # port 3102
│   └── landing/                 # port 3202
├── rankpilot/                   # Automated SEO Engine (General Sans / Nunito Sans)
│   ├── backend/                 # port 8103 — 165 tests
│   ├── dashboard/               # port 3103
│   └── landing/                 # port 3203
├── flowsend/                    # Smart Email Marketing (Satoshi / Source Sans 3)
│   ├── backend/                 # port 8104 — 151 tests
│   ├── dashboard/               # port 3104
│   └── landing/                 # port 3204
├── spydrop/                     # Competitor Intelligence (Geist / Geist)
│   ├── backend/                 # port 8105 — 156 tests
│   ├── dashboard/               # port 3105
│   └── landing/                 # port 3205
├── postpilot/                   # Social Media Automation (Plus Jakarta Sans / Quicksand)
│   ├── backend/                 # port 8106 — 157 tests
│   ├── dashboard/               # port 3106
│   └── landing/                 # port 3206
├── adscale/                     # AI Ad Campaign Manager (Anybody / Manrope)
│   ├── backend/                 # port 8107 — 164 tests
│   ├── dashboard/               # port 3107
│   └── landing/                 # port 3207
├── shopchat/                    # AI Shopping Assistant (Outfit / Lexend)
│   ├── backend/                 # port 8108 — 113 tests
│   ├── dashboard/               # port 3108
│   └── landing/                 # port 3208
│
├── llm-gateway/                 # Centralized AI provider routing — port 8200
│   └── backend/                 # 42 tests
├── admin/                       # Super admin dashboard — port 8300
│   ├── backend/                 # 34 tests
│   └── dashboard/
├── master-landing/              # Suite-wide marketing landing page
├── _template/                   # Service scaffold for new services
├── e2e/                         # Playwright end-to-end tests (25+ spec files)
└── plan/                        # Architecture docs, backlog
```

---

## Data Model (Core — Backend Service)

```
┌──────────┐     ┌──────────┐     ┌──────────────┐
│  Tenant   │────<│   User   │────<│ Subscription │
└──────────┘     └──────────┘     └──────────────┘
                       │
                       │ has many
                       ▼
                 ┌──────────┐
                 │  Store    │──────────────────────────────────────────────┐
                 └──────────┘                                              │
                   │       │       │        │         │         │           │
          has many │       │       │        │         │         │           │
                   ▼       ▼       ▼        ▼         ▼         ▼           ▼
            ┌─────────┐ ┌───────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐
            │ Product  │ │ Order │ │Discount│ │Customer│ │Category│ │ Supplier │
            └─────────┘ └───────┘ └────────┘ └────────┘ └────────┘ └──────────┘
                │           │                     │          │           │
                │           │                     │          │           │
                ▼           ▼                     ▼          ▼           ▼
          ┌───────────┐ ┌────────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐
          │ Variant    │ │Fulfillment │ │ Wishlist │ │Collection│ │ Supplier   │
          └───────────┘ │+ Refund    │ │ Review   │ └──────────┘ │ Product    │
                │       └────────────┘ └──────────┘              └────────────┘
                ▼
          ┌───────────┐     ┌──────┐
          │  Review    │     │Theme │
          └───────────┘     └──────┘
```

> **Dropshipping-specific:** The `Supplier` and `SupplierProduct` models are core
> to the business model — they link each product to its source supplier, track
> supplier costs (for profit calculation), and enable auto-fulfillment. The
> `Fulfillment` model tracks supplier order placement and shipping (distinct from
> traditional ecommerce shipping management — store owners never touch the product).

### Core Tables (Backend)

**Existing tables (Features 1-7.5 + Polish Plan):**
`users`, `stores`, `products`, `product_variants`, `orders`, `order_items`,
`subscriptions`, `customer_accounts`, `customer_wishlists`, `customer_addresses`

**New tables by feature:**

| Feature | New Tables |
|---------|-----------|
| F8: Discount Codes & Promotions | `discounts`, `discount_rules` |
| F9: Product Categories & Collections | `categories`, `collections`, `product_categories`, `product_collections` |
| F10: Supplier Management & Order Fulfillment | `suppliers`, `supplier_products`, `fulfillments` |
| F11: Transactional Email Notifications | `email_templates`, `email_logs` |
| F12: Product Reviews & Ratings | `reviews` |
| F13: Profit & Performance Analytics | `analytics_events` |
| F14: Refunds & Customer Disputes | `refund_requests`, `refunds`, `store_credits` |
| F15: Store Customization & Themes | `store_themes`, `custom_pages`, `navigation_menus` |
| F16: Tax Calculation | `tax_rates` |
| F17: Advanced Search & Filtering | `search_queries` |
| F18: Upsell, Cross-sell & Recommendations | `product_relations` |
| F19: Customer Segmentation & Groups | `customer_segments` |
| F20: Gift Cards | `gift_cards`, `gift_card_transactions` |
| F21: Multi-Currency & International | `store_currencies` |
| F22: Custom Domains | `store_domains` |
| F23: Webhooks & Public API | `api_keys`, `webhook_endpoints`, `webhook_deliveries` |
| F24: Multi-User & Team Access | `store_team_members`, `team_invites`, `activity_logs` |
| F25: Notifications & Alerts Center | `notifications`, `notification_preferences` |
| F26: Bulk Operations & Import/Export | `import_jobs` |
| F28: Fraud Detection | `fraud_checks` |
| A8: AI Shopping Assistant | `chat_conversations` |
| F29: A/B Testing | `ab_tests`, `ab_test_assignments`, `ab_test_conversions` |

## ServiceBridge — Platform Event Integration

The ServiceBridge connects the dropshipping platform to all 8 SaaS services via
HMAC-signed HTTP webhooks dispatched through Celery background tasks.

### Event Flow

```
Product CRUD / Order Events / Customer Registration
  └─→ fire_platform_event() [lazy import]
        └─→ dispatch_platform_event.delay() [Celery task]
              ├─→ Query ServiceIntegration for connected services
              ├─→ Filter by EVENT_SERVICE_MAP
              ├─→ POST to each service with HMAC-SHA256 signature
              └─→ Record BridgeDelivery for each attempt
```

### Event → Service Mapping

| Event | Target Services |
|-------|----------------|
| `product.created` | ContentForge, RankPilot, TrendScout, PostPilot, AdScale, ShopChat |
| `product.updated` | ContentForge, RankPilot, ShopChat |
| `order.created` | FlowSend, SpyDrop |
| `order.shipped` | FlowSend |
| `customer.created` | FlowSend |

### Key Files

- `dropshipping/backend/app/tasks/bridge_tasks.py` — Celery task with EVENT_SERVICE_MAP
- `dropshipping/backend/app/services/bridge_service.py` — HMAC signing, activity queries
- `dropshipping/backend/app/api/bridge.py` — REST API for dashboard (5 endpoints)
- `dropshipping/backend/app/models/bridge_delivery.py` — Delivery tracking model
- Each service: `{service}/backend/app/api/webhooks.py` — Platform event receiver

### Dashboard UI

- **Service Activity page** (`/stores/[id]/services/activity`): Full activity log with KPIs, filters, pagination
- **Store overview widget**: Recent service activity card on store dashboard
- **Product/Order detail panels**: Per-resource service status grid (8 services)
- **Services hub health indicators**: Last event status, failure count badges

---

## Kubernetes Architecture

```
                         ┌─────────────────┐
                         │  ingress-nginx   │
                         │  (+ cert-manager)│
                         └────────┬────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
     dashboard.platform.com      │          *.platform.com
              │           api.platform.com       (wildcard)
              ▼                   ▼                   ▼
       ┌───────────┐       ┌───────────┐       ┌───────────┐
       │ Dashboard  │       │  Backend   │       │ Storefront │
       │ (Next.js)  │       │ (FastAPI)  │       │ (Next.js)  │
       │ 2 replicas │       │ 3 replicas │       │ 2 replicas │
       └───────────┘       └───────────┘       └───────────┘
                                  │
                         ┌────────┴────────┐
                         │                 │
                   ┌───────────┐     ┌───────────┐
                   │  Celery    │     │  Celery    │
                   │  Workers   │     │   Beat     │
                   │ 2 replicas │     │ 1 replica  │
                   └───────────┘     └───────────┘

       ┌─────────────────────────────────────────────────┐
       │            Automation Service                    │
       │  (Standalone — extractable as separate product)  │
       ├─────────────────────────────────────────────────┤
       │                                                  │
       │  ┌──────────────┐  ┌──────────────┐              │
       │  │ Automation    │  │ Automation   │              │
       │  │ API (FastAPI) │  │ Celery       │              │
       │  │ port 8001     │  │ Workers (2)  │              │
       │  └──────────────┘  └──────────────┘              │
       │         │           ┌──────────────┐              │
       │         │           │ Automation   │              │
       │         │           │ Celery Beat  │              │
       │         │           │ (1 replica)  │              │
       │         │           └──────────────┘              │
       └─────────┼───────────────────────────────────────┘
                 │
                 │  Internal API calls
                 ▼
          ┌───────────┐
          │  Backend   │
          │ (FastAPI)  │
          └───────────┘

         ┌─────────┬─────────┐
         │                   │
   ┌───────────┐       ┌───────────┐
   │ PostgreSQL │       │   Redis    │
   │ (StatefulSet│      │  (cache +  │
   │  or managed)│      │   broker)  │
   └───────────┘       └───────────┘
```

> **Automation service boundary:** The automation service runs as an independent
> deployment with its own API, Celery workers, and Beat scheduler. It communicates
> with the core backend via internal HTTP API calls (not direct DB access to core
> tables). This allows the automation service to be extracted into a standalone
> product without modifying the core platform.

---

## API Convention

### Core Backend API (port 8000)
- All endpoints prefixed: `/api/v1/`
- Auth header: `Authorization: Bearer <jwt>`
- Response format: `{ "data": ..., "error": null }` or `{ "data": null, "error": { "code": "...", "message": "..." } }`
- Pagination: `?page=1&per_page=20` → response includes `{ "total": N, "page": 1, "per_page": 20 }`
- Store-scoped endpoints: `/api/v1/stores/{store_id}/products`
- Webhooks: `/api/v1/webhooks/stripe`

### Automation Service API (port 8001)
- All endpoints prefixed: `/api/v1/automation/`
- Auth: Forwards the user's JWT to the core backend for validation (or uses service-to-service auth token)
- Store-scoped endpoints: `/api/v1/automation/stores/{store_id}/research`
- Same response format and pagination conventions as the core backend
- Dashboard calls the automation API directly for automation-related pages (research, SEO, email flows)

### Inter-Service Communication
- Automation → Backend: Internal HTTP calls to `http://backend:8000/api/v1/...`
- Backend → Automation: Event-driven via Redis pub/sub or direct HTTP calls
- Shared data: Only `store_id`, `user_id`, `product_id` references — no shared tables
- In local dev: both services share the same PostgreSQL instance (separate schemas or tables)
- In production: can use separate databases for full isolation

---

## Local Development (Devcontainer)

Open the project in VS Code → "Reopen in Container". The devcontainer starts:
- **PostgreSQL 16** at `db:5432` (user: `dropship`, pass: `dropship_dev`, db: `dropshipping`)
- **Redis 7** at `redis:6379`
- **Python 3.12** + **Node.js 20** in the workspace container

Environment variables are pre-configured in `docker-compose.yml`:
- `DATABASE_URL=postgresql+asyncpg://dropship:dropship_dev@db:5432/dropshipping`
- `REDIS_URL=redis://redis:6379/0`
- `CELERY_BROKER_URL=redis://redis:6379/1`

```bash
# Inside the devcontainer — run each in a separate terminal:

# Dropshipping Backend API
cd dropshipping/backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Dropshipping Dashboard
cd dropshipping/dashboard && npm run dev       # → localhost:3000

# Storefront
cd dropshipping/storefront && npm run dev -- -p 3001  # → localhost:3001

# Celery worker
cd dropshipping/backend && celery -A app.tasks.celery_app worker --loglevel=info

# LLM Gateway
cd llm-gateway/backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8200

# SaaS Services (each in its own terminal)
cd trendscout/backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8101
cd contentforge/backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8102
# ... etc. See Makefile for shortcuts.
```

### Ports
| Port | Service                      |
| ---- | ---------------------------- |
| 8000 | Dropshipping Backend (FastAPI) |
| 3000 | Dropshipping Dashboard (Next.js) |
| 3001 | Storefront (Next.js)          |
| 8101-8108 | SaaS Services (FastAPI)  |
| 3101-3108 | SaaS Dashboards (Next.js) |
| 3201-3208 | SaaS Landing Pages (Next.js) |
| 8200 | LLM Gateway (FastAPI)         |
| 8300 | Admin Dashboard (FastAPI)     |
| 5432 | PostgreSQL                    |
| 6379 | Redis                         |

---

## Shared Packages

### packages/py-core (ecomm_core)

Provides consistent cross-service infrastructure:
- **Auth**: JWT token creation/validation, `get_current_user` dependency
- **Billing**: Stripe subscription router, webhook handler, billing service
- **DB**: SQLAlchemy engine factory, session management, migration helpers
- **Models**: Base model, User, Subscription, API Key models
- **Health**: Standardized `/health` endpoint
- **Testing**: Schema-based test isolation fixtures, test helpers
- **Config**: `BaseServiceConfig` with common settings (incl. `platform_webhook_secret`)

### packages/py-connectors (ecomm_connectors)

Platform adapters for e-commerce integrations:
- **Base adapter**: Abstract interface for platform operations
- **Shopify connector**: Product sync, order import, inventory management
- **WooCommerce connector**: REST API v3 integration
- **Factory**: `get_connector(platform_name)` for dynamic platform selection

---

## Background Tasks (Celery)

The platform uses Celery with Redis as the message broker for background task processing.
Tasks are defined in `backend/app/tasks/` and cover all asynchronous operations.

### Task Modules

| Module | Tasks | Purpose |
|--------|-------|---------|
| `email_tasks.py` | 9 tasks | Transactional emails (order confirmation, shipping, delivery, refund, welcome, password reset, gift card, team invite, low stock) |
| `webhook_tasks.py` | 1 task | HTTP webhook delivery with HMAC-SHA256 signing, failure tracking, auto-disable after 10 failures |
| `bridge_tasks.py` | 1 task | ServiceBridge: dispatch platform events to connected SaaS services with HMAC signing |
| `notification_tasks.py` | 4 tasks | In-app dashboard notifications (order events, reviews, low stock, fraud alerts) |
| `fraud_tasks.py` | 1 task | Automated fraud risk scoring (5 heuristic signals, 0-100 score, auto-flag high/critical) |
| `order_tasks.py` | 3 tasks | Post-payment orchestration, auto-fulfillment via suppliers, fulfillment status checks |
| `analytics_tasks.py` | 2 tasks | Daily revenue aggregation, notification cleanup (90-day read notifications) |

**Total: 21 task functions across 7 modules.**

### Infrastructure

- **Sync DB access:** Tasks use `SyncSessionFactory` (`backend/app/tasks/db.py`) with `psycopg2` driver since Celery workers run synchronously
- **Celery Beat schedule:** 3 periodic tasks — daily analytics (2 AM), notification cleanup (3 AM), fulfillment checks (every 30 min)
- **JSON serialization:** All UUIDs passed as strings to `.delay()`, converted back inside tasks
- **Retry policy:** Most tasks use `max_retries=3` with 30-60s backoff

### Event Flow

```
Stripe Webhook (checkout.session.completed)
  └─→ process_paid_order.delay(order_id)
        ├─→ run_fraud_check(order_id)           [sync — needs result]
        ├─→ send_order_confirmation.delay()       [async]
        ├─→ dispatch_webhook_event.delay()        [async]
        ├─→ create_order_notification.delay()     [async]
        ├─→ send_low_stock_alert.delay()          [if variant <= 5 units]
        └─→ auto_fulfill_order.delay()            [if not fraud-flagged]
              ├─→ send_order_shipped.delay()
              ├─→ dispatch_webhook_event.delay("order.shipped")
              └─→ create_order_notification.delay("order_shipped")
```

### Integration Points

Tasks are dispatched from these API endpoints:
- `POST /api/v1/webhooks/stripe` → `process_paid_order.delay()`
- `POST /stores/{id}/orders/{id}/fulfill` → shipped email + webhook + notification
- `POST /stores/{id}/orders/{id}/deliver` → delivered email + webhook + notification
- `POST /stores/{id}/customers/register` → `send_welcome_email.delay()`
- `POST /stores/{id}/customers/forgot-password` → `send_password_reset.delay()`
- `POST /stores/{id}/refunds` → refund email + webhook

---

## Testing Strategy

### Backend Unit/Integration Tests

Backend tests use `pytest` with `httpx.AsyncClient` for API testing. Tests are located in `dropshipping/backend/tests/` and each service's `backend/tests/`.

**Key patterns:**
- Async test functions with `@pytest.mark.asyncio`
- `conftest.py` provides `client` (AsyncClient) and `db` (async session) fixtures
- **Schema-based test isolation**: Each service uses dedicated PostgreSQL schema (e.g. `trendscout_test`, `dropshipping_test`)
- Raw asyncpg for schema creation/termination (not SQLAlchemy — more robust)
- `search_path` set via SQLAlchemy `connect` event listener
- DB cleanup via `TRUNCATE TABLE ... CASCADE` per test (not `drop_all`/`create_all`)
- `NullPool` for test engine to avoid async connection-sharing issues
- Tests create their own data via API calls (register user → create store → create resource)

**Dropshipping test files (44+ files, 580 tests):** Includes `test_bridge_api.py`, `test_bridge_service.py`, `test_bridge_tasks.py` (39 ServiceBridge tests) plus all existing feature tests.

**8 standalone services** each have their own test suites (~1,180 tests total). Each service uses schema-based test isolation in the shared PostgreSQL database.

### E2E Tests (Playwright)

E2E tests use Playwright and are located in `e2e/tests/`. They test the full stack: dashboard (Next.js) → backend API (FastAPI) → database (PostgreSQL).

**Key patterns:**
- Each test file tests both **empty state** and **populated data** scenarios
- Populated-data tests seed data via direct API calls (using helper functions in `helpers.ts`)
- API helpers include retry logic for race conditions (async DB commit may not be visible immediately)
- Tests use `page.reload()` + `waitForLoadState("networkidle")` after data mutations to ensure fresh data

**Test helpers** (`e2e/tests/helpers.ts`):
- `registerAndLogin()` — creates a new user + store, returns auth token and store info
- `apiPost()` / `apiGet()` — authenticated API calls with retry on 400/401/404
- `createProductAPI()`, `createOrderAPI()`, `createCategoryAPI()`, etc. — resource creation helpers
- `createRefundAPI()`, `createReviewAPI()` — complex resource creation (requires order/product chain)

**E2E test files (187+ tests across 24 spec files):**

| File | Covers |
|------|--------|
| `dashboard/auth.spec.ts` | User registration, login, redirects |
| `dashboard/stores.spec.ts` | Store CRUD, store listing |
| `dashboard/products.spec.ts` | Product CRUD, populated table |
| `dashboard/orders.spec.ts` | Order listing, detail, status updates |
| `dashboard/fulfillment.spec.ts` | Fulfillment flow, tracking |
| `dashboard/discounts.spec.ts` | Discount CRUD, populated table with formatting |
| `dashboard/categories.spec.ts` | Category CRUD, nested subcategories |
| `dashboard/suppliers.spec.ts` | Supplier CRUD, populated table with linked products |
| `dashboard/gift-cards.spec.ts` | Gift card CRUD, formatted balances |
| `dashboard/tax-refunds.spec.ts` | Tax rates + refunds, Decimal formatting |
| `dashboard/teams-webhooks.spec.ts` | Team invites + webhook config |
| `dashboard/reviews-analytics.spec.ts` | Reviews + analytics pages |
| `dashboard/currency-domain.spec.ts` | Currency settings + domain config |
| `dashboard/advanced-features.spec.ts` | Segments, upsells, A/B tests, bulk ops |
| `dashboard/themes-email.spec.ts` | Theme settings + email templates |
| `dashboard/billing.spec.ts` | Billing page, subscription |
| `dashboard/seed-data.spec.ts` | Seed data verification (24 tests) |
| `dashboard/phase2-polish.spec.ts` | KPIs, order notes, CSV export, command palette, inventory alerts |
| `dashboard/service-bridge.spec.ts` | ServiceBridge API, activity page, services hub, product service status |
| `storefront/browse.spec.ts` | Product browsing, homepage |
| `storefront/cart-checkout.spec.ts` | Cart, checkout, payment |
| `storefront/categories-search.spec.ts` | Storefront category nav + search |
| `storefront/customer-accounts.spec.ts` | Customer auth, orders, wishlist |
| `storefront/policies.spec.ts` | Policy pages |
| `storefront/seed-data.spec.ts` | Seed data verification (12 tests) |

### Common Frontend Bug Patterns (Caught by E2E Tests)

1. **Paginated response unwrapping**: Backend returns `{ items: [...], total, ... }`, frontend expects array. Fix: `Array.isArray(raw) ? raw : raw.items ?? []`
2. **Decimal string serialization**: SQLAlchemy Decimal → JSON string (`"25.00"` not `25`). Fix: `Number(value).toFixed(2)`
3. **String reduce concatenation**: `reduce((sum, r) => sum + r.amount, 0)` with string amounts produces `"049.99"`. Fix: `Number(r.amount)`
4. **Field name mismatches**: Frontend uses `order_number` but backend returns `order_id`. Fix: Align interfaces with backend schemas
5. **HTML5 step validation**: `<input step="0.01">` blocks values like 8.875. Fix: `step="any"`
6. **Slug self-collision on update**: `generate_unique_slug()` finds the SAME entity in DB, appends `-2`, then on next save finds `-2` and uses original. Fix: pass `exclude_id` to exclude the current entity from uniqueness check

---

## Phase 2 Polish Features

### Theme Engine v2
- **13 block types** (5 new: product_carousel, testimonials, countdown_timer, video_banner, trust_badges)
- **11 preset themes** (4 new: Coastal, Monochrome, Cyberpunk, Terracotta)
- Hero banner product showcase mode with configurable overlays
- Block config editor in dashboard with per-block-type forms
- Enhanced typography: weight, letter-spacing, line-height controls

### Animation & Motion
- Motion primitives: `FadeIn`, `StaggerChildren`, `SlideIn`, `ScaleIn`, `ScrollReveal`
- Staggered grid animations on all product/category listing pages
- Micro-interactions: add-to-cart pulse, cart badge bounce, spring-based mobile menu
- Loading skeletons (shimmer effect) on product pages
- Animated count-up numbers on dashboard analytics

### Dashboard Enhancements
- **Store overview KPI dashboard**: 4 metric cards with animated count-up, recent orders, quick actions
- **Platform home dashboard**: Aggregate KPIs across stores, store cards with mini metrics
- **Command palette** (`Cmd+K`/`Ctrl+K`): Fuzzy search pages/actions with keyboard navigation
- **Notification badges**: Unread count on Notifications, pending orders on Orders sidebar item
- **Enhanced analytics**: Customer metrics, order status bar chart, animated counters

### Data & QoL
- **CSV export**: `GET /stores/{id}/exports/{orders|products|customers}` endpoints + dashboard buttons
- **Order notes**: Internal memo field on orders (auto-save textarea in dashboard)
- **Inventory alerts**: Low-stock warning cards on store overview (variants with < 5 units)
- **Seed enhancements**: Order notes on demo orders, Cyberpunk theme assignment

---

## Phase 3: Monorepo with Shared Packages (Current)

Phase 3 restructured the 8 SaaS services into a flat monorepo with shared packages,
replacing the old `services/` subdirectory with root-level service directories and
introducing `packages/py-core` and `packages/py-connectors` for shared code.

### Products

| # | Name | Tagline | Fonts | Backend | Tests |
|---|------|---------|-------|---------|-------|
| A1 | **TrendScout** | AI-Powered Product Research | Syne / DM Sans | :8101 | 158 |
| A2 | **ContentForge** | AI Product Content Generator | Clash Display / Satoshi | :8102 | 116 |
| A3 | **RankPilot** | Automated SEO Engine | General Sans / Nunito Sans | :8103 | 165 |
| A4 | **FlowSend** | Smart Email Marketing | Satoshi / Source Sans 3 | :8104 | 151 |
| A5 | **SpyDrop** | Competitor Intelligence | Geist / Geist | :8105 | 156 |
| A6 | **PostPilot** | Social Media Automation | Plus Jakarta Sans / Quicksand | :8106 | 157 |
| A7 | **AdScale** | AI Ad Campaign Manager | Anybody / Manrope | :8107 | 164 |
| A8 | **ShopChat** | AI Shopping Assistant | Outfit / Lexend | :8108 | 113 |

### Architecture Principles

1. **Shared Packages**: Common auth, billing, DB logic in `packages/py-core` (`ecomm_core`)
2. **Platform Connectors**: Shopify/WooCommerce adapters in `packages/py-connectors` (`ecomm_connectors`)
3. **Config-Driven UI**: Dashboard and landing page customized via `service.config.ts` / `landing.config.ts`
4. **Scaffolded from Template**: New services created from `_template/` scaffold
5. **ServiceBridge**: Platform events (product/order/customer) auto-dispatched to connected services
6. **Distinctive Typography**: Each service uses unique fonts (no Inter/Roboto/Arial/Space Grotesk)

### Per-Service Stack

Each service is a complete SaaS application:
- **Backend**: FastAPI + SQLAlchemy 2.0 async + Celery + Alembic + `ecomm_core`
- **Dashboard**: Next.js 16 (App Router) + Tailwind + config-driven branding
- **Landing Page**: Next.js 16 (static export) with CSS animations
- **Platform Events**: `POST /api/v1/webhooks/platform-events` receiver with HMAC verification

### Platform Integration

The dropshipping backend integrates with services via:
- `ServiceIntegration` model tracking provisioned accounts per user
- `POST /api/v1/auth/provision` endpoint in each service for user provisioning
- `GET /api/v1/usage` endpoint for usage metrics
- **ServiceBridge**: Automatic event dispatch via Celery (product/order/customer lifecycle)
- Dashboard sidebar "AI & Automation" section with Service Activity page
- LLM Gateway for centralized AI provider routing

### Metrics

| Component | Count |
|---|---|
| Standalone SaaS services | 8 |
| Dropshipping backend tests | 580 |
| TrendScout tests | 158 |
| ContentForge tests | 116 |
| RankPilot tests | 165 |
| FlowSend tests | 151 |
| SpyDrop tests | 156 |
| PostPilot tests | 157 |
| AdScale tests | 164 |
| ShopChat tests | 113 |
| py-core tests | 19 |
| py-connectors tests | 40 |
| LLM Gateway tests | 42 |
| Admin tests | 34 |
| **Total backend tests** | **~1,895** |
| E2E test spec files | 25+ |
| Celery task functions | 21 (incl. bridge) |
| ServiceBridge event types | 5 |

See [SERVICES.md](SERVICES.md) for full service architecture details.
