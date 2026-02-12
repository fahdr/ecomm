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
| Automation service | Separate Python/FastAPI service | Decoupled from core backend for independent scaling and future extraction as standalone product |

---

## Project Structure

```
dropshipping-platform/
├── backend/                     # Python (FastAPI)
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── database.py          # SQLAlchemy engine + session
│   │   ├── models/              # SQLAlchemy models
│   │   │   ├── user.py
│   │   │   ├── store.py
│   │   │   ├── product.py
│   │   │   ├── subscription.py
│   │   │   └── order.py
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── api/                 # FastAPI routers
│   │   │   ├── auth.py
│   │   │   ├── stores.py
│   │   │   ├── products.py
│   │   │   ├── subscriptions.py
│   │   │   └── webhooks.py
│   │   ├── services/            # Business logic (core backend only)
│   │   │   ├── auth_service.py
│   │   │   ├── store_service.py
│   │   │   ├── product_service.py
│   │   │   └── stripe_service.py
│   │   ├── tasks/               # Celery tasks (core backend only)
│   │   │   ├── celery_app.py    # Celery instance + config
│   │   │   └── store_tasks.py   # Store-related background tasks
│   │   └── utils/               # Shared utilities
│   ├── alembic/                 # Database migrations
│   │   └── versions/
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pyproject.toml
│
├── dashboard/                   # Next.js (Admin Dashboard)
│   ├── src/
│   │   ├── app/                 # App Router pages
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx         # Dashboard home
│   │   │   ├── login/
│   │   │   ├── register/
│   │   │   ├── stores/
│   │   │   ├── products/
│   │   │   ├── analytics/
│   │   │   └── settings/
│   │   ├── components/          # Reusable UI components
│   │   │   ├── ui/              # Shadcn/ui components
│   │   │   ├── layout/          # Sidebar, header, etc.
│   │   │   └── features/        # Feature-specific components
│   │   ├── lib/                 # Utilities
│   │   │   ├── api.ts           # API client (fetch wrapper)
│   │   │   └── auth.ts          # JWT token management
│   │   └── hooks/               # Custom React hooks
│   ├── package.json
│   ├── Dockerfile
│   └── next.config.js
│
├── storefront/                  # Next.js (Customer-Facing Stores)
│   ├── src/
│   │   ├── app/                 # App Router pages
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx         # Store homepage
│   │   │   ├── products/
│   │   │   ├── cart/
│   │   │   ├── checkout/
│   │   │   └── blog/
│   │   ├── components/
│   │   ├── lib/
│   │   │   ├── api.ts           # Backend API client
│   │   │   └── store-context.ts # Current store (from subdomain)
│   │   └── middleware.ts        # Subdomain → store_id resolution
│   ├── package.json
│   ├── Dockerfile
│   └── next.config.js
│
├── automation/                  # Python (Automation Service — Phase 2: Features A1-A8)
│   │                            # Standalone service: can be extracted as a
│   │                            # separate product in the future.
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point (port 8001)
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── database.py          # SQLAlchemy engine + session (own DB or shared)
│   │   ├── models/              # SQLAlchemy models (automation-specific)
│   │   │   ├── watchlist_item.py    # Product research results
│   │   │   ├── blog_post.py         # AI-generated blog posts
│   │   │   ├── email_flow.py        # Email automation flows
│   │   │   ├── email_event.py       # Email event tracking
│   │   │   ├── competitor.py        # Competitor monitoring
│   │   │   ├── social_post.py       # Social media posts
│   │   │   └── ad_campaign.py       # Ad campaign tracking
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── api/                 # FastAPI routers
│   │   │   ├── research.py      # Product research endpoints
│   │   │   ├── import_.py       # Product import endpoints
│   │   │   ├── seo.py           # SEO automation endpoints
│   │   │   ├── email.py         # Email automation endpoints
│   │   │   ├── competitors.py   # Competitor monitoring endpoints
│   │   │   ├── social.py        # Social media automation endpoints
│   │   │   └── ads.py           # Ad campaign management endpoints
│   │   ├── services/            # Business logic
│   │   │   ├── research_service.py      # AliExpress, Reddit, Trends
│   │   │   ├── ai_service.py            # Claude API for content generation
│   │   │   ├── import_service.py        # Product import pipeline
│   │   │   ├── seo_service.py           # Sitemap, schema, blog generation
│   │   │   ├── email_service.py         # SendGrid integration
│   │   │   ├── image_service.py         # Image download + optimization
│   │   │   ├── competitor_service.py    # Competitor scraping + analysis
│   │   │   ├── social_service.py        # Social media posting (Meta, TikTok)
│   │   │   └── ads_service.py           # Google/Meta ads management
│   │   ├── tasks/               # Celery tasks
│   │   │   ├── celery_app.py    # Own Celery instance + config
│   │   │   ├── research_tasks.py    # Daily product research
│   │   │   ├── import_tasks.py      # Product import pipeline
│   │   │   ├── seo_tasks.py         # Weekly SEO optimization
│   │   │   ├── email_tasks.py       # Email flow execution
│   │   │   ├── competitor_tasks.py  # Daily competitor scanning
│   │   │   ├── social_tasks.py      # Social media scheduling/posting
│   │   │   └── ads_tasks.py         # Ad performance sync + optimization
│   │   └── utils/               # Shared utilities
│   ├── alembic/                 # Own database migrations
│   │   └── versions/
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pyproject.toml
│
├── k8s/                         # Kubernetes manifests
│   ├── base/                    # Shared resources
│   │   ├── namespace.yaml
│   │   ├── postgres.yaml
│   │   ├── redis.yaml
│   │   └── secrets.yaml
│   ├── backend/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── hpa.yaml
│   ├── celery/
│   │   ├── worker-deployment.yaml
│   │   ├── beat-deployment.yaml
│   │   └── flower-deployment.yaml
│   ├── automation/
│   │   ├── deployment.yaml          # Automation API
│   │   ├── service.yaml
│   │   ├── worker-deployment.yaml   # Automation Celery workers
│   │   └── beat-deployment.yaml     # Automation Celery Beat
│   ├── dashboard/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── ingress.yaml
│   ├── storefront/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── ingress.yaml         # Wildcard subdomain routing
│   └── kustomization.yaml
│
├── docker-compose.yml           # Local development
├── .github/
│   └── workflows/
│       ├── backend.yml          # pytest + deploy
│       ├── automation.yml       # pytest + deploy (automation service)
│       ├── dashboard.yml        # build + deploy
│       └── storefront.yml       # build + deploy
└── plan/                        # This planning directory
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

## Data Model (Automation Service)

```
                          ┌──────────┐
                          │  Store    │  (referenced by store_id, owned by backend)
                          └──────────┘
                    ┌─────────┼──────────┬──────────────┐
           has many │         │          │              │
                    ▼         ▼          ▼              ▼
      ┌────────────────┐ ┌───────────┐ ┌────────────┐ ┌────────────┐
      │ WatchlistItem   │ │ BlogPost  │ │ Competitor  │ │ SocialPost │
      │ (research       │ │ (SEO      │ │ (monitor    │ │ (social    │
      │  results)       │ │  content) │ │  rivals)    │ │  marketing)│
      └────────────────┘ └───────────┘ └────────────┘ └────────────┘
                                            │
                                   has many │
                                            ▼
                                   ┌──────────────────┐
                                   │ CompetitorProduct │
                                   └──────────────────┘

                          ┌──────────┐
                          │  Store    │
                          └──────────┘
                    ┌─────────┼──────────┐
           has many │         │          │
                    ▼         ▼          ▼
            ┌───────────────┐ ┌──────────┐ ┌────────────┐
            │ EmailFlow      │ │AdCampaign│ │ AdAccount  │
            │ EmailCampaign  │ └──────────┘ └────────────┘
            │ EmailUnsubscribe│
            └───────────────┘
                   │
          has many │
                   ▼
            ┌────────────┐
            │ EmailEvent  │
            └────────────┘
```

**Automation tables:** `watchlist_items`, `blog_posts`, `email_flows`, `email_campaigns`,
`email_events`, `email_unsubscribes`, `competitors`, `competitor_products`, `social_posts`,
`ad_campaigns`, `ad_accounts`

> **Service boundary:** The automation service references `store_id` and `user_id`
> from the core backend but does NOT own those tables. It communicates with the
> backend via its internal HTTP API to fetch store/product data. This keeps the
> services decoupled so the automation service can be extracted as a standalone
> product in the future.

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

# Backend API
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Automation Service API
cd automation && uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Dashboard
cd dashboard && npm run dev          # → localhost:3000

# Storefront
cd storefront && npm run dev -- -p 3001  # → localhost:3001

# Backend Celery worker
cd backend && celery -A app.tasks.celery_app worker --loglevel=info

# Backend Celery Beat (scheduler)
cd backend && celery -A app.tasks.celery_app beat --loglevel=info

# Automation Celery worker
cd automation && celery -A app.tasks.celery_app worker --loglevel=info -Q automation

# Automation Celery Beat (scheduler)
cd automation && celery -A app.tasks.celery_app beat --loglevel=info

# Flower (task monitor) — optional, monitors both backends
cd backend && celery -A app.tasks.celery_app flower --port=5555
```

### Ports
| Port | Service                      |
| ---- | ---------------------------- |
| 8000 | Backend (FastAPI)             |
| 8001 | Automation Service (FastAPI)  |
| 3000 | Dashboard (Next.js)           |
| 3001 | Storefront (Next.js)          |
| 5432 | PostgreSQL                    |
| 6379 | Redis                         |
| 5555 | Flower                        |

---

## Automation Service — Design Principles

**Goal:** The automation service (Phase 2: Features A1-A8) is
designed as an independent, self-contained service that can be extracted into a
standalone product in the future without requiring changes to the core platform.
Phase 2 is implemented after Phase 1 (core platform features) is stable.

### Separation Rules

1. **Own codebase:** Lives in `/automation/` with its own `pyproject.toml`,
   `requirements.txt`, `Dockerfile`, and Alembic migrations.

2. **Own database tables:** Automation-specific models (`WatchlistItem`,
   `BlogPost`, `EmailFlow`, `EmailEvent`) are defined and migrated independently.
   In local dev they share the same PostgreSQL instance; in production they can
   use a separate database.

3. **No direct imports from backend:** The automation service MUST NOT import
   code from `backend/`. Shared concepts (e.g. store ID, user ID) are passed
   via API calls or message payloads, not Python imports.

4. **Communication via HTTP API:** The automation service calls the core
   backend's REST API to fetch store, product, and user data. It authenticates
   using the user's JWT (forwarded from the dashboard) or a service-to-service
   token.

5. **Own Celery instance:** The automation service runs its own Celery workers
   and Beat scheduler, using a dedicated Redis queue (`-Q automation`). This
   prevents automation tasks from competing with core backend tasks.

6. **Dashboard integration:** The dashboard (Next.js) calls the automation
   service API directly for automation-specific pages (research results, SEO
   overview, email flow builder). The dashboard's API client is configured
   with both backend and automation service base URLs.

### Extracting as a Standalone Product

To extract the automation service as a separate product:

1. Deploy `automation/` independently with its own infrastructure.
2. Replace internal backend API calls with the public API (add auth).
3. Provide its own user management or integrate with an OAuth provider.
4. The core dropshipping platform continues to work without the automation
   service — it simply loses the automation features.

### What Each Feature Owns

| Feature | Service Scope | Key Models | Celery Tasks |
| ------- | ------------- | ---------- | ------------ |
| A1: Product Research Automation | Research endpoints + AI scoring | `WatchlistItem` | `daily_product_research`, `run_all_stores_research` |
| A2: AI Product Import | Import pipeline + AI content | (creates products via backend API) | `import_product` |
| A3: SEO Automation | Sitemap, schema, blog | `BlogPost` | `weekly_seo_optimization` |
| A4: Marketing Email Automation | Email flows, campaigns, abandoned cart | `EmailFlow`, `EmailCampaign`, `EmailEvent`, `EmailUnsubscribe` | `evaluate_flow_triggers`, `execute_flow_step`, `send_broadcast` |
| A5: Competitor Monitoring | Competitor store scraping + alerts | `Competitor`, `CompetitorProduct` | `daily_competitor_scan` |
| A6: Social Media Automation | Auto-post products to social platforms | `SocialPost` | `schedule_social_posts`, `post_to_social` |
| A7: Ad Campaign Management | Google/Meta ad automation | `AdCampaign`, `AdAccount` | `sync_ad_performance`, `optimize_campaigns` |

---

## Testing Strategy

### Backend Unit/Integration Tests

Backend tests use `pytest` with `httpx.AsyncClient` for API testing. Tests are located in `backend/tests/`.

**Key patterns:**
- Async test functions with `@pytest.mark.asyncio`
- `conftest.py` provides `client` (AsyncClient) and `db` (async session) fixtures
- DB cleanup via `TRUNCATE TABLE ... CASCADE` per test (not `drop_all`/`create_all`)
- `NullPool` for test engine to avoid async connection-sharing issues
- Tests create their own data via API calls (register user → create store → create resource)

**Test files (35+ files, 488 tests):** `test_health.py`, `test_auth.py`, `test_public.py`, `test_products.py`, `test_stores.py`, `test_subscriptions.py`, `test_orders.py`, `test_customers.py`, `test_discounts.py`, `test_categories.py`, `test_suppliers.py`, `test_reviews.py`, `test_analytics.py`, `test_refunds.py`, `test_themes.py`, `test_tax.py`, `test_search.py`, `test_upsells.py`, `test_segments.py`, `test_gift_cards.py`, `test_currency.py`, `test_domains.py`, `test_store_webhooks.py`, `test_teams.py`, `test_notifications.py`, `test_bulk.py`, `test_fraud.py`, `test_ab_tests.py`, `test_services.py`, `test_service_schemas.py`, `test_service_integration_service.py`

Additionally, **8 standalone services** each have their own test suites (~543 tests total across all services).

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

## Phase 2: Standalone SaaS Products (A1-A8)

Phase 2 replaced the monolithic `automation/` service with **8 independent, separately
hostable SaaS products**. Each product has its own backend, dashboard, landing page,
database, users, billing, and API.

### Products

| # | Name | Tagline | Backend | Dashboard | Landing | Tests |
|---|------|---------|---------|-----------|---------|-------|
| A1 | **TrendScout** | AI-Powered Product Research | :8101 | :3101 | :3201 | 67 |
| A2 | **ContentForge** | AI Product Content Generator | :8102 | :3102 | :3202 | 45 |
| A3 | **RankPilot** | Automated SEO Engine | :8103 | :3103 | :3203 | 74 |
| A4 | **FlowSend** | Smart Email Marketing | :8104 | :3104 | :3204 | 87 |
| A5 | **SpyDrop** | Competitor Intelligence | :8105 | :3105 | :3205 | 43 |
| A6 | **PostPilot** | Social Media Automation | :8106 | :3106 | :3206 | 62 |
| A7 | **AdScale** | AI Ad Campaign Manager | :8107 | :3107 | :3207 | 77 |
| A8 | **ShopChat** | AI Shopping Assistant | :8108 | :3108 | :3208 | 88 |

### Architecture Principles

1. **Complete Independence**: No shared libraries, databases, or imports between services
2. **Config-Driven**: Dashboard and landing page are customized via `service.config.ts`
3. **Scaffolded from Template**: All services share the same structure (`services/_template/`)
4. **REST API Integration**: Services communicate only via HTTP APIs
5. **Own Billing**: Each service has its own Stripe subscription management

### Per-Service Stack

Each service is a complete SaaS application:
- **Backend**: FastAPI + SQLAlchemy 2.0 async + Celery + Alembic
- **Dashboard**: Next.js 16 (App Router) + Tailwind + shadcn/ui
- **Landing Page**: Next.js 16 (static export) with CSS animations
- **Database**: Own PostgreSQL database
- **Cache/Queue**: Own Redis instance (or DB number in dev)

### Platform Integration

The dropshipping backend integrates with services via:
- `ServiceIntegration` model tracking provisioned accounts per user
- `POST /api/v1/auth/provision` endpoint in each service for user provisioning
- `GET /api/v1/usage` endpoint for usage metrics
- Dashboard sidebar "AI & Automation" section with 8 service pages
- Bundle pricing: Starter includes 2 services (Free tier), Growth/Pro includes all 8

### Metrics

| Component | Count |
|---|---|
| Standalone services | 8 |
| Service feature tests | ~543 |
| Platform integration tests | 152 |
| Total backend tests | 488 |
| Master landing page | 7 components (static export) |
| Alembic migrations | 14 |
| DB tables | ~38 |

See [SERVICES.md](SERVICES.md) for full service architecture details.
