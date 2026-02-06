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
│   │   ├── services/            # Business logic
│   │   │   ├── auth_service.py
│   │   │   ├── store_service.py
│   │   │   ├── product_service.py
│   │   │   ├── ai_service.py
│   │   │   └── stripe_service.py
│   │   ├── tasks/               # Celery tasks
│   │   │   ├── celery_app.py    # Celery instance + config
│   │   │   ├── store_tasks.py
│   │   │   ├── research_tasks.py
│   │   │   ├── import_tasks.py
│   │   │   └── marketing_tasks.py
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
│       ├── dashboard.yml        # build + deploy
│       └── storefront.yml       # build + deploy
└── plan/                        # This planning directory
```

---

## Data Model (Core)

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

**Key tables:** `tenants`, `users`, `stores`, `products`, `product_variants`, `orders`, `order_items`, `subscriptions`, `invoices`, `watchlist_items`, `blog_posts`

---

## Kubernetes Architecture

```
                    ┌─────────────────┐
                    │  ingress-nginx   │
                    │  (+ cert-manager)│
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     dashboard.platform.com  │    *.platform.com
              │              │         (wildcard)
              ▼              ▼              ▼
       ┌───────────┐  ┌───────────┐  ┌───────────┐
       │ Dashboard  │  │  Backend   │  │ Storefront │
       │ (Next.js)  │  │ (FastAPI)  │  │ (Next.js)  │
       │ 2 replicas │  │ 3 replicas │  │ 2 replicas │
       └───────────┘  └───────────┘  └───────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
              ┌───────────┐    ┌───────────┐
              │  Celery    │    │  Celery    │
              │  Workers   │    │   Beat     │
              │ 2 replicas │    │ 1 replica  │
              └───────────┘    └───────────┘
                    │
              ┌───────────┐
              │  Flower    │
              │ (monitor)  │
              └───────────┘
                    │
         ┌─────────┴─────────┐
         │                   │
   ┌───────────┐       ┌───────────┐
   │ PostgreSQL │       │   Redis    │
   │  (StatefulSet      │  (cache +  │
   │   or managed)      │   broker)  │
   └───────────┘       └───────────┘
```

---

## API Convention

- All endpoints prefixed: `/api/v1/`
- Auth header: `Authorization: Bearer <jwt>`
- Response format: `{ "data": ..., "error": null }` or `{ "data": null, "error": { "code": "...", "message": "..." } }`
- Pagination: `?page=1&per_page=20` → response includes `{ "total": N, "page": 1, "per_page": 20 }`
- Store-scoped endpoints: `/api/v1/stores/{store_id}/products`
- Webhooks: `/api/v1/webhooks/stripe`

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

# Dashboard
cd dashboard && npm run dev          # → localhost:3000

# Storefront
cd storefront && npm run dev -- -p 3001  # → localhost:3001

# Celery worker
cd backend && celery -A app.tasks.celery_app worker --loglevel=info

# Celery Beat (scheduler)
cd backend && celery -A app.tasks.celery_app beat --loglevel=info

# Flower (task monitor) — optional
cd backend && celery -A app.tasks.celery_app flower --port=5555
```

### Ports
| Port | Service          |
| ---- | ---------------- |
| 8000 | Backend (FastAPI) |
| 3000 | Dashboard (Next.js) |
| 3001 | Storefront (Next.js) |
| 5432 | PostgreSQL        |
| 6379 | Redis             |
| 5555 | Flower            |
