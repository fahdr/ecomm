# Architecture & Stack Decisions

## Decisions Made

| Decision          | Choice                          | Rationale                                              |
| ----------------- | ------------------------------- | ------------------------------------------------------ |
| Backend language  | Python 3.12+ / FastAPI          | Developer expertise, strong AI/scraping ecosystem      |
| Frontend          | Next.js 14+ (App Router)        | SEO, component ecosystem (Shadcn/ui), industry standard|
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
├── automation/                  # Python (Automation Service — Features 8-11)
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
│   │   │   └── email_event.py       # Email event tracking
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── api/                 # FastAPI routers
│   │   │   ├── research.py      # Product research endpoints
│   │   │   ├── import_.py       # Product import endpoints
│   │   │   ├── seo.py           # SEO automation endpoints
│   │   │   └── email.py         # Email automation endpoints
│   │   ├── services/            # Business logic
│   │   │   ├── research_service.py      # AliExpress, Reddit, Trends
│   │   │   ├── ai_service.py            # Claude API for content generation
│   │   │   ├── import_service.py        # Product import pipeline
│   │   │   ├── seo_service.py           # Sitemap, schema, blog generation
│   │   │   ├── email_service.py         # SendGrid integration
│   │   │   └── image_service.py         # Image download + optimization
│   │   ├── tasks/               # Celery tasks
│   │   │   ├── celery_app.py    # Own Celery instance + config
│   │   │   ├── research_tasks.py    # Daily product research
│   │   │   ├── import_tasks.py      # Product import pipeline
│   │   │   ├── seo_tasks.py         # Weekly SEO optimization
│   │   │   └── email_tasks.py       # Email flow execution
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
                 │  Store    │
                 └──────────┘
                   │       │
          has many │       │ has many
                   ▼       ▼
            ┌─────────┐ ┌───────┐
            │ Product  │ │ Order │
            └─────────┘ └───────┘
                │
                │ has many
                ▼
          ┌───────────┐
          │ Variant    │
          └───────────┘
```

**Core tables (backend):** `tenants`, `users`, `stores`, `products`, `product_variants`, `orders`, `order_items`, `subscriptions`, `invoices`

## Data Model (Automation Service)

```
                 ┌──────────┐
                 │  Store    │  (referenced by store_id, owned by backend)
                 └──────────┘
                   │       │
          has many │       │ has many
                   ▼       ▼
      ┌────────────────┐  ┌───────────┐
      │ WatchlistItem   │  │ BlogPost  │
      │ (research       │  │ (SEO      │
      │  results)       │  │  content) │
      └────────────────┘  └───────────┘

                 ┌──────────┐
                 │  Store    │
                 └──────────┘
                   │
          has many │
                   ▼
            ┌───────────┐
            │ EmailFlow  │
            └───────────┘
                   │
          has many │
                   ▼
            ┌────────────┐
            │ EmailEvent  │
            └────────────┘
```

**Automation tables:** `watchlist_items`, `blog_posts`, `email_flows`, `email_events`

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

**Goal:** The automation service (Features 8-11) is designed as an independent,
self-contained service that can be extracted into a standalone product in the
future without requiring changes to the core platform.

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
| F8: Product Research | Research endpoints + AI scoring | `WatchlistItem` | `daily_product_research` |
| F9: Product Import   | Import pipeline + AI content | (creates products via backend API) | `import_product` |
| F10: SEO Automation  | Sitemap, schema, blog | `BlogPost` | `weekly_seo_optimization` |
| F11: Email Automation| Email flows + SendGrid | `EmailFlow`, `EmailEvent` | `send_email_flow`, `abandoned_cart` |
