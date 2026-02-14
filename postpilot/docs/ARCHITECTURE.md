# PostPilot Architecture

> Part of [PostPilot](README.md) documentation

This document describes the technical architecture, tech stack, project structure, database models, and design decisions for PostPilot.

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

## Project Structure

```
postpilot/
|-- README.md                          # Service overview and quick reference
|-- Makefile                           # Build, test, and run targets
|-- .env.example                       # Environment variable template
|-- docker-compose.yml                 # Docker services configuration
|-- docs/                              # Documentation (this directory)
|   |-- README.md
|   |-- SETUP.md
|   |-- ARCHITECTURE.md
|   |-- API_REFERENCE.md
|   |-- TESTING.md
|   |-- QA_ENGINEER.md
|   |-- PROJECT_MANAGER.md
|   |-- END_USER.md
|   |-- IMPLEMENTATION_STEPS.md
|-- backend/
|   |-- Dockerfile                     # Backend container image
|   |-- alembic/                       # Database migration scripts
|   |   |-- env.py                     # Alembic async engine configuration
|   |   |-- versions/                  # Migration version files
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

## Database Models

### Core Domain Models

#### User (`users` table)

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `email` | String(255), unique, indexed | User email address |
| `hashed_password` | String(255) | Bcrypt-hashed password |
| `plan` | Enum(PlanTier) | free, pro, enterprise |
| `stripe_customer_id` | String(255), nullable | Stripe customer ID |
| `external_platform_id` | UUID, nullable | Dropshipping platform user ID |
| `external_store_id` | UUID, nullable | Dropshipping platform store ID |
| `created_at` | DateTime | Account creation timestamp |
| `updated_at` | DateTime | Last modification timestamp |

**Relationships:** `subscription` (one-to-one), `api_keys` (one-to-many), `social_accounts` (one-to-many)

#### SocialAccount (`social_accounts` table)

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `user_id` | UUID (FK -> users) | Owning user |
| `platform` | Enum(SocialPlatform) | instagram, facebook, tiktok |
| `account_name` | String(255) | Display name (e.g., @mybrand) |
| `account_id_external` | String(255) | Platform-specific account ID |
| `access_token_enc` | String(1024), nullable | Encrypted OAuth access token |
| `refresh_token_enc` | String(1024), nullable | Encrypted OAuth refresh token |
| `is_connected` | Boolean, default True | Active connection status |
| `connected_at` | DateTime, nullable | When connected |
| `created_at` | DateTime | Record creation timestamp |

**Enum:** `SocialPlatform` -- `instagram`, `facebook`, `tiktok`

**Relationships:** `owner` (User, backref), `posts` (Post, back_populates)

#### Post (`posts` table)

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `user_id` | UUID (FK -> users) | Owning user |
| `account_id` | UUID (FK -> social_accounts) | Target social account |
| `content` | Text | Post caption text |
| `media_urls` | ARRAY(String) | Attached media URLs |
| `hashtags` | ARRAY(String) | Hashtag list (without # prefix) |
| `platform` | String(50) | Target platform (denormalized) |
| `status` | Enum(PostStatus) | draft, scheduled, posted, failed |
| `scheduled_for` | DateTime, nullable, indexed | Scheduled publish time |
| `posted_at` | DateTime, nullable | Actual publish timestamp |
| `error_message` | Text, nullable | Failure details |
| `created_at` | DateTime | Record creation timestamp |
| `updated_at` | DateTime | Last modification timestamp |

**Enum:** `PostStatus` -- `draft`, `scheduled`, `posted`, `failed`

**Relationships:** `account` (SocialAccount, back_populates), `metrics` (PostMetrics, one-to-one)

#### PostMetrics (`post_metrics` table)

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `post_id` | UUID (FK -> posts, unique) | One-to-one with Post |
| `impressions` | Integer, default 0 | Display count |
| `reach` | Integer, default 0 | Unique viewer count |
| `likes` | Integer, default 0 | Like/reaction count |
| `comments` | Integer, default 0 | Comment count |
| `shares` | Integer, default 0 | Share/repost count |
| `clicks` | Integer, default 0 | Link click count |
| `fetched_at` | DateTime | Last metrics refresh |

**Relationships:** `post` (Post, back_populates)

#### ContentQueue (`content_queue` table)

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `user_id` | UUID (FK -> users) | Owning user |
| `product_data` | JSON | Product information for AI input |
| `ai_generated_content` | Text, nullable | AI-generated caption |
| `platforms` | ARRAY(String) | Target platforms |
| `status` | Enum(QueueStatus) | pending, approved, rejected, posted |
| `created_at` | DateTime | Record creation timestamp |
| `updated_at` | DateTime | Last modification timestamp |

**Enum:** `QueueStatus` -- `pending`, `approved`, `rejected`, `posted`

**Relationships:** `owner` (User, backref)

### Standard Models (Shared Template)

#### Subscription (`subscriptions` table)

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `user_id` | UUID (FK -> users, unique) | Owning user (one-to-one) |
| `stripe_subscription_id` | String(255), nullable | Stripe subscription ID |
| `status` | Enum(SubscriptionStatus) | active, trialing, past_due, canceled, etc. |
| `plan` | Enum(PlanTier) | free, pro, enterprise |
| `current_period_start` | DateTime, nullable | Billing period start |
| `current_period_end` | DateTime, nullable | Billing period end |
| `cancel_at_period_end` | Boolean, default False | Scheduled cancellation flag |
| `created_at` | DateTime | Subscription creation timestamp |
| `updated_at` | DateTime | Last modification timestamp |

**Enum:** `SubscriptionStatus` -- `active`, `trialing`, `past_due`, `canceled`, `unpaid`, `incomplete`

#### ApiKey (`api_keys` table)

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `user_id` | UUID (FK -> users) | Owning user |
| `key_hash` | String(64), unique, indexed | SHA-256 hash of raw key |
| `prefix` | String(16) | Key prefix (e.g., `po_live_`) |
| `name` | String(255) | User-assigned key name |
| `scopes` | ARRAY(String) | Permission scopes |
| `is_active` | Boolean, default True | Active status |
| `last_used_at` | DateTime, nullable | Last usage timestamp |
| `created_at` | DateTime | Key creation timestamp |

**Relationships:** `owner` (User, backref)

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

---

## Key Architectural Decisions

### 1. Config-Driven Dashboard

All branding, navigation, and plan tiers are defined in `service.config.ts`. Changing this single file updates the entire dashboard UI.

**Rationale:** Enables rapid white-labeling and multi-tenant deployments without code changes.

### 2. Mock OAuth

Social account connection simulates OAuth by generating mock tokens. Real OAuth integration would redirect to platform authorization URLs.

**Rationale:** Allows full testing and development without platform API credentials. Real OAuth is Phase 1 implementation.

### 3. Mock AI Captions

The `caption_service.py` generates template-based captions using product data. With an Anthropic API key, this would call Claude for real AI generation.

**Rationale:** Provides functional scaffold for testing while allowing seamless upgrade to real LLM integration.

### 4. Soft Disconnect

Disconnecting a social account sets `is_connected=False` and clears tokens, but preserves the record for post history and analytics.

**Rationale:** Users can reconnect later without losing historical data. Supports analytics continuity.

### 5. User Isolation

All queries filter by `user_id`. Tests verify that user A cannot see or modify user B's resources.

**Rationale:** Critical for multi-tenant SaaS security. Enforced at service layer, verified by comprehensive tests.

### 6. Stripe Mock Mode

When `STRIPE_SECRET_KEY` is empty, checkout creates subscriptions directly in the database without calling Stripe. This enables full testing without Stripe credentials.

**Rationale:** Reduces external dependencies during development and testing. Production deployment sets real Stripe key.

### 7. Sentinel Value Pattern

The `update_post` function uses Python's `Ellipsis` (`...`) as a sentinel to distinguish "field not provided" from "set field to None". This allows clearing `scheduled_for` by passing `None` explicitly.

**Rationale:** Enables partial updates with explicit null values. Common FastAPI pattern for PATCH endpoints.

---

## Plan Limit Enforcement

Plan limits are defined in `backend/app/constants/plans.py`:

| Tier | Posts/Month (`max_items`) | Social Accounts (`max_secondary`) | API Access |
|------|--------------------------|-----------------------------------|------------|
| Free | 10 | 1 | No |
| Pro | 200 | 10 | Yes |
| Enterprise | Unlimited (-1) | Unlimited (-1) | Yes |

Limit enforcement happens in:
- `account_service.py` -- checks `max_secondary` before connecting a new account
- `post_service.py` -- checks `max_items` (posts created this calendar month) before creating a post

---

## Platform Event Webhook

Each service receives platform events from the dropshipping backend via `POST /api/v1/webhooks/platform-events`. Events are HMAC-SHA256 signed using `platform_webhook_secret`. The receiver verifies the signature and routes events to service-specific handlers.

**Example events:**
- `user.provisioned` -- New user created from platform
- `subscription.updated` -- Plan change notification

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
| Body | Quicksand | Rounded, friendly, pairs well with Plus Jakarta Sans |

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

*See also: [Setup](SETUP.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md) · [README](README.md)*
