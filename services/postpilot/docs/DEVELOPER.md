# Developer Guide

**For Developers:** PostPilot is a standalone SaaS product for social media automation. It supports multi-platform posting across Instagram, Facebook, and TikTok, with AI-powered caption generation, content queue management, post scheduling with calendar views, and engagement analytics. It can operate independently or integrate with the dropshipping platform via API provisioning.

---

## Tech Stack

| Layer | Technology | Version/Notes |
|-------|-----------|---------------|
| Backend API | FastAPI | Async, ASGI, OpenAPI docs auto-generated |
| ORM | SQLAlchemy 2.0 | Async with `AsyncSession`, mapped columns |
| Database | PostgreSQL 16 | UUID primary keys, ARRAY columns, JSON fields |
| Cache / Queue Broker | Redis 7 | Separate DB indices for cache (0), broker (1), results (2) |
| Task Queue | Celery | Async task processing for scheduled post publication |
| Migrations | Alembic | Async engine, auto-generated migrations |
| Dashboard | Next.js 16 | App Router, React Server Components, client pages |
| Styling | Tailwind CSS | OKLCH color system, custom design tokens |
| Landing Page | Next.js 16 | Static export, marketing page with pricing |
| Auth | JWT (Bearer) + API Keys | Access/refresh token pair, SHA-256 hashed API keys |
| Billing | Stripe (mock mode) | Checkout sessions, customer portal, webhooks |

---

## Local Development

### Ports

| Service | Port | Description |
|---------|------|-------------|
| Backend API | `8106` | FastAPI server with auto-reload |
| Dashboard | `3106` | Next.js dev server |
| Landing Page | `3206` | Next.js static landing page |
| PostgreSQL | `5506` | Database |
| Redis | `6406` | Cache and Celery broker |

### Quick Start

```bash
# From /workspaces/ecomm/services/postpilot/
make install      # Install Python + Node dependencies
make migrate      # Run Alembic migrations
make start        # Start backend + dashboard + landing
```

### Access Points

- **API**: http://localhost:8106
- **API Docs (Swagger)**: http://localhost:8106/docs
- **Dashboard**: http://localhost:3106
- **Landing Page**: http://localhost:3206

---

## Environment Variables

Set in `.env` or via Docker Compose. See `.env.example` for defaults.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...@db:5506/postpilot` | Async database connection string |
| `DATABASE_URL_SYNC` | `postgresql://...@db:5506/postpilot` | Sync URL for Alembic |
| `REDIS_URL` | `redis://redis:6406/0` | Redis connection for caching |
| `CELERY_BROKER_URL` | `redis://redis:6406/1` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://redis:6406/2` | Celery results storage |
| `JWT_SECRET_KEY` | (required) | Secret for signing JWT tokens |
| `STRIPE_SECRET_KEY` | (empty = mock mode) | Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | (empty = skip verification) | Stripe webhook signing secret |
| `STRIPE_PRO_PRICE_ID` | (empty) | Stripe Price ID for Pro tier |
| `STRIPE_ENTERPRISE_PRICE_ID` | (empty) | Stripe Price ID for Enterprise tier |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8106` | Backend URL for dashboard/landing |

---

## Project Structure

```
services/postpilot/
|-- README.md                          # Service overview and quick reference
|-- Makefile                           # Build, test, and run targets
|-- .env.example                       # Environment variable template
|-- docs/                              # Documentation (this directory)
|   |-- DEVELOPER.md
|   |-- QA_ENGINEER.md
|   |-- PROJECT_MANAGER.md
|   |-- END_USER.md
|   |-- IMPLEMENTATION_STEPS.md
|-- backend/
|   |-- alembic/                       # Database migration scripts
|   |   |-- env.py                     # Alembic async engine configuration
|   |-- app/
|   |   |-- main.py                    # FastAPI app entry point
|   |   |-- config.py                  # Settings loaded from environment
|   |   |-- database.py                # Async engine + session factory
|   |   |-- api/
|   |   |   |-- __init__.py            # Router aggregation
|   |   |   |-- deps.py                # Auth dependencies (JWT + API key)
|   |   |   |-- auth.py                # Register, login, refresh, profile, provision
|   |   |   |-- accounts.py            # Social account CRUD
|   |   |   |-- posts.py               # Post CRUD, scheduling, calendar
|   |   |   |-- queue.py               # Content queue CRUD, AI generation, approve/reject
|   |   |   |-- analytics.py           # Overview + per-post metrics
|   |   |   |-- billing.py             # Plans, checkout, portal, subscription
|   |   |   |-- api_keys.py            # API key create, list, revoke
|   |   |   |-- usage.py               # Usage tracking endpoint
|   |   |   |-- health.py              # Health check endpoint
|   |   |   |-- webhooks.py            # Stripe webhook handler
|   |   |-- models/
|   |   |   |-- base.py                # SQLAlchemy DeclarativeBase
|   |   |   |-- user.py                # User model with PlanTier enum
|   |   |   |-- social_account.py      # SocialAccount model (SocialPlatform enum)
|   |   |   |-- post.py                # Post model (PostStatus enum)
|   |   |   |-- post_metrics.py        # PostMetrics model (one-to-one with Post)
|   |   |   |-- content_queue.py       # ContentQueue model (QueueStatus enum)
|   |   |   |-- subscription.py        # Subscription model (SubscriptionStatus enum)
|   |   |   |-- api_key.py             # ApiKey model (SHA-256 hashed)
|   |   |-- services/
|   |   |   |-- auth_service.py        # Registration, login, JWT, API key auth
|   |   |   |-- account_service.py     # Social account connect/disconnect/list
|   |   |   |-- post_service.py        # Post CRUD, scheduling, calendar grouping
|   |   |   |-- caption_service.py     # AI caption generation (mock + template-based)
|   |   |   |-- analytics_service.py   # Aggregated metrics + per-post metrics
|   |   |   |-- billing_service.py     # Stripe checkout, portal, overview
|   |   |-- schemas/
|   |   |   |-- auth.py                # Auth request/response Pydantic models
|   |   |   |-- social.py              # Social account, post, queue, analytics schemas
|   |   |   |-- billing.py             # Billing request/response schemas
|   |   |-- constants/
|   |   |   |-- plans.py               # PlanLimits dataclass + PLAN_LIMITS dict
|   |   |-- tasks/
|   |   |   |-- celery_app.py          # Celery application configuration
|   |   |-- utils/
|   |       |-- helpers.py             # Shared utility functions
|   |-- tests/
|       |-- conftest.py                # Async fixtures, DB setup/teardown
|       |-- test_auth.py               # 10 auth endpoint tests
|       |-- test_accounts.py           # 16 social account tests
|       |-- test_posts.py              # 20 post management tests
|       |-- test_queue.py              # 22 content queue tests
|       |-- test_billing.py            # 9 billing tests
|       |-- test_api_keys.py           # 5 API key tests
|       |-- test_health.py             # 1 health check test
|-- dashboard/
|   |-- src/
|   |   |-- service.config.ts          # Branding, navigation, plans (single source of truth)
|   |   |-- app/
|   |   |   |-- layout.tsx             # Root layout with fonts + theme
|   |   |   |-- page.tsx               # Dashboard home (KPI cards, quick actions)
|   |   |   |-- accounts/page.tsx      # Social account management (connect/disconnect)
|   |   |   |-- posts/page.tsx         # Post list with CRUD
|   |   |   |-- queue/page.tsx         # Content queue + AI generation + calendar sidebar
|   |   |   |-- billing/page.tsx       # Subscription plans + checkout
|   |   |   |-- api-keys/page.tsx      # API key management
|   |   |   |-- settings/page.tsx      # User settings
|   |   |   |-- login/page.tsx         # Login form
|   |   |   |-- register/page.tsx      # Registration form
|   |   |-- components/
|   |   |   |-- shell.tsx              # Layout shell (sidebar + top bar)
|   |   |   |-- sidebar.tsx            # Collapsible sidebar driven by service.config.ts
|   |   |   |-- top-bar.tsx            # Top navigation bar
|   |   |   |-- motion.tsx             # Animation primitives (FadeIn, StaggerChildren, etc.)
|   |   |   |-- ui/                    # Shadcn/ui components (card, button, badge, etc.)
|   |   |-- lib/
|   |       |-- api.ts                 # API client with auth token management
|   |       |-- auth.ts                # Auth helpers (token storage, refresh)
|   |       |-- utils.ts               # Tailwind class merge utility
|   |-- package.json
|   |-- tsconfig.json
|   |-- next.config.ts
|-- landing/
    |-- src/
    |   |-- landing.config.ts          # Landing page configuration
    |   |-- app/
    |   |   |-- page.tsx               # Landing home page
    |   |   |-- pricing/page.tsx       # Pricing page
    |   |   |-- layout.tsx             # Landing layout
    |   |-- components/
    |       |-- hero.tsx               # Hero section
    |       |-- features.tsx           # Feature showcase
    |       |-- pricing-cards.tsx      # Pricing tier cards
    |       |-- how-it-works.tsx       # How it works section
    |       |-- stats-bar.tsx          # Stats bar
    |       |-- cta.tsx                # Call to action
    |       |-- navbar.tsx             # Navigation bar
    |       |-- footer.tsx             # Footer
    |-- package.json
    |-- tsconfig.json
    |-- next.config.ts
```

---

## Testing

### Running Tests

```bash
# All 62 backend tests
make test-backend

# With verbose output
cd backend && pytest -v

# Run a specific test file
cd backend && pytest tests/test_posts.py -v

# Run a specific test
cd backend && pytest tests/test_posts.py::test_create_post_as_draft -v
```

### Test Distribution (62 tests total)

| Test File | Tests | Coverage Area |
|-----------|-------|---------------|
| `test_queue.py` | 22 | Content queue CRUD, AI generation, approve/reject workflow |
| `test_posts.py` | 20 | Post CRUD, scheduling, calendar, pagination, filtering |
| `test_accounts.py` | 16 | Social account connect/disconnect, plan limits, isolation |
| `test_auth.py` | 10 | Registration, login, refresh, profile, duplicate handling |
| `test_billing.py` | 9 | Plan listing, checkout, overview, subscription management |
| `test_api_keys.py` | 5 | Key create, list, revoke, auth via X-API-Key |
| `test_health.py` | 1 | Health check endpoint |

### Test Infrastructure

- **Framework**: pytest + pytest-asyncio + httpx.AsyncClient
- **Database**: Same PostgreSQL instance, tables truncated between tests via `TRUNCATE CASCADE`
- **Connection cleanup**: All non-self DB connections terminated before truncation to prevent deadlocks
- **Fixtures**: `client` (async HTTP client), `auth_headers` (registered user JWT), `register_and_login` helper
- **Stripe**: Mock mode (empty `STRIPE_SECRET_KEY`) -- no real API calls in tests

---

## API Conventions

### Authentication

All protected endpoints require a `Bearer` JWT token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Alternatively, use an API key via the `X-API-Key` header:

```
X-API-Key: po_live_<random_token>
```

### Response Format

- **Success**: JSON body with resource data
- **List endpoints**: Paginated with `{ items: [...], total: N, page: N, per_page: N }`
- **Create**: Returns `201 Created` with the new resource
- **Delete**: Returns `204 No Content` (empty body)
- **Errors**: `{ detail: "error message" }` with appropriate HTTP status code

### Status Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `201` | Created |
| `204` | No Content (delete) |
| `400` | Bad Request (invalid state transition, business rule violation) |
| `401` | Unauthorized (missing or invalid auth) |
| `403` | Forbidden (plan limit reached) |
| `404` | Not Found |
| `409` | Conflict (duplicate email) |
| `422` | Validation Error (Pydantic) |

### Plan Limit Enforcement

Plan limits are defined in `backend/app/constants/plans.py`:

| Tier | Posts/Month (`max_items`) | Social Accounts (`max_secondary`) | API Access |
|------|--------------------------|-----------------------------------|------------|
| Free | 10 | 1 | No |
| Pro | 200 | 10 | Yes |
| Enterprise | Unlimited (-1) | Unlimited (-1) | Yes |

Limit enforcement happens in:
- `account_service.py` -- checks `max_secondary` before connecting a new account
- `post_service.py` -- checks `max_items` (posts created this calendar month) before creating a post

### Sentinel Value Pattern

The `update_post` function uses Python's `Ellipsis` (`...`) as a sentinel to distinguish "field not provided" from "set field to None". This allows clearing `scheduled_for` by passing `None` explicitly.

---

## Design System

### Colors (OKLCH)

| Token | Value | Hex Fallback | Usage |
|-------|-------|-------------|-------|
| Primary | `oklch(0.65 0.22 350)` | `#ec4899` (Hot Pink) | Buttons, links, active states |
| Accent | `oklch(0.72 0.18 330)` | `#f472b6` (Soft Pink) | Hover states, highlights |

### Typography

| Role | Font Family | Notes |
|------|-------------|-------|
| Heading | Plus Jakarta Sans | Rounded geometric sans, friendly and modern |
| Body | Inter | Highly legible for content-heavy dashboards |

### Dashboard Navigation

Driven by `service.config.ts`. The sidebar renders these items:

| Label | Route | Icon |
|-------|-------|------|
| Dashboard | `/` | LayoutDashboard |
| Queue | `/queue` | ListOrdered |
| Calendar | `/calendar` | Calendar |
| Accounts | `/accounts` | Users |
| Analytics | `/analytics` | BarChart3 |
| Templates | `/templates` | FileText |
| API Keys | `/api-keys` | Key |
| Billing | `/billing` | CreditCard |
| Settings | `/settings` | Settings |

---

## Key Architectural Decisions

1. **Config-driven dashboard**: All branding, navigation, and plan tiers are defined in `service.config.ts`. Changing this single file updates the entire dashboard UI.

2. **Mock OAuth**: Social account connection simulates OAuth by generating mock tokens. Real OAuth integration would redirect to platform authorization URLs.

3. **Mock AI captions**: The `caption_service.py` generates template-based captions using product data. With an Anthropic API key, this would call Claude for real AI generation.

4. **Soft disconnect**: Disconnecting a social account sets `is_connected=False` and clears tokens, but preserves the record for post history and analytics.

5. **User isolation**: All queries filter by `user_id`. Tests verify that user A cannot see or modify user B's resources.

6. **Stripe mock mode**: When `STRIPE_SECRET_KEY` is empty, checkout creates subscriptions directly in the database without calling Stripe. This enables full testing without Stripe credentials.

---

## Database Models

### Core Domain Models

| Model | Table | Key Fields | Relationships |
|-------|-------|------------|---------------|
| `User` | `users` | email, hashed_password, plan (PlanTier enum), stripe_customer_id, external_platform_id | subscription, api_keys, social_accounts |
| `SocialAccount` | `social_accounts` | platform (SocialPlatform enum), account_name, access_token_enc, is_connected | owner (User), posts |
| `Post` | `posts` | content, media_urls (ARRAY), hashtags (ARRAY), platform, status (PostStatus enum), scheduled_for | account (SocialAccount), metrics (PostMetrics) |
| `PostMetrics` | `post_metrics` | impressions, reach, likes, comments, shares, clicks, fetched_at | post (one-to-one with Post) |
| `ContentQueue` | `content_queue` | product_data (JSON), ai_generated_content, platforms (ARRAY), status (QueueStatus enum) | owner (User) |

### Standard Models (shared template)

| Model | Table | Purpose |
|-------|-------|---------|
| `Subscription` | `subscriptions` | Stripe subscription state tracking |
| `ApiKey` | `api_keys` | SHA-256 hashed API keys with scopes |

### Enums

| Enum | Values | Used In |
|------|--------|---------|
| `PlanTier` | free, pro, enterprise | User.plan |
| `SocialPlatform` | instagram, facebook, tiktok | SocialAccount.platform |
| `PostStatus` | draft, scheduled, posted, failed | Post.status |
| `QueueStatus` | pending, approved, rejected, posted | ContentQueue.status |
| `SubscriptionStatus` | active, trialing, past_due, canceled, unpaid, incomplete | Subscription.status |

---

## Service Layer Functions

### account_service.py

| Function | Description |
|----------|-------------|
| `connect_account(db, user, platform, account_name, account_id_external)` | Connect a social account (enforces `max_secondary` plan limit) |
| `disconnect_account(db, user, account_id)` | Soft-disconnect (set `is_connected=False`, clear tokens) |
| `list_accounts(db, user)` | List all accounts (connected + disconnected) |
| `get_account(db, user, account_id)` | Get single account by ID |

### post_service.py

| Function | Description |
|----------|-------------|
| `create_post(db, user, account_id, content, platform, ...)` | Create post (enforces `max_items` monthly limit) |
| `update_post(db, user, post_id, ...)` | Partial update (only draft/scheduled) |
| `delete_post(db, user, post_id)` | Delete post (only draft/scheduled) |
| `get_post(db, user, post_id)` | Get single post |
| `list_posts(db, user, page, per_page, status, platform)` | Paginated list with filters |
| `schedule_post(db, user, post_id, scheduled_for)` | Schedule a draft (rejects past times) |
| `get_calendar_posts(db, user, start_date, end_date)` | Group posts by date for calendar view |

### caption_service.py

| Function | Description |
|----------|-------------|
| `generate_caption(product_data, platform, tone)` | Generate AI caption + hashtags from product data |
| `suggest_hashtags(product_data, platform)` | Extract keywords and combine with platform-specific trending tags |

### analytics_service.py

| Function | Description |
|----------|-------------|
| `get_analytics_overview(db, user)` | Aggregated totals (impressions, reach, likes, etc.) + avg engagement rate |
| `get_post_metrics(db, user, post_id)` | Metrics for a single post |
| `get_all_post_metrics(db, user, page, per_page)` | Paginated metrics for all published posts |
