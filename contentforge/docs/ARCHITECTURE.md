# Architecture Guide

> Part of [ContentForge](README.md) documentation

This document describes the technical architecture, design decisions, database schema, and key patterns used throughout ContentForge.

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend API | FastAPI + SQLAlchemy 2.0 (async) | Python 3.12 |
| Database | PostgreSQL | 16 |
| Cache / Queue Broker | Redis | 7 |
| Task Queue | Celery | 5.x |
| Image Processing | Pillow | Latest |
| Dashboard | Next.js (App Router) | 16 |
| Dashboard Styling | Tailwind CSS | 4.x |
| Landing Page | Next.js (static export) | 16 |
| ORM Migrations | Alembic | Latest |
| Testing | pytest + pytest-asyncio + httpx | Latest |

---

## Project Structure

```
contentforge/
  backend/
    app/
      api/                         # API route handlers (FastAPI routers)
        __init__.py                # Router registration
        auth.py                    # POST /auth/register, /auth/login, /auth/refresh, /auth/me, /auth/provision
        billing.py                 # GET /billing/plans, POST /billing/checkout, /billing/portal, GET /billing/current, /billing/overview
        api_keys.py                # POST /api-keys, GET /api-keys, DELETE /api-keys/{id}
        content.py                 # POST /content/generate, /content/generate/bulk, GET /content/jobs, /content/jobs/{id}, DELETE /content/jobs/{id}, PATCH /content/{id}
        templates.py               # POST /templates, GET /templates, /templates/{id}, PATCH /templates/{id}, DELETE /templates/{id}
        images.py                  # GET /images, /images/{id}, DELETE /images/{id}
        health.py                  # GET /health
        usage.py                   # GET /usage
        webhooks.py                # POST /webhooks/stripe, /webhooks/platform-events
        deps.py                    # get_current_user, get_current_user_or_api_key dependencies
      models/                      # SQLAlchemy 2.0 async models
        base.py                    # Declarative base
        user.py                    # User model + PlanTier enum
        api_key.py                 # ApiKey model (SHA-256 hashed keys)
        subscription.py            # Subscription model + SubscriptionStatus enum
        generation.py              # GenerationJob + GeneratedContent models
        image_job.py               # ImageJob model
        template.py                # Template model (system + custom)
      services/                    # Business logic layer
        auth_service.py            # User registration, login, JWT tokens, API key auth
        content_service.py         # Generation job lifecycle, plan limit checks, mock AI content
        image_service.py           # Image CRUD, mock image processing
        pricing_service.py         # Markup calculation, psychological rounding strategies
        billing_service.py         # Stripe checkout/portal, subscription management, usage metrics
        template_seeder.py         # Seeds system templates at startup
      schemas/                     # Pydantic request/response models
        auth.py                    # Auth endpoint schemas
        content.py                 # Content, template, image schemas
        billing.py                 # Plan, checkout, subscription, usage schemas
      constants/
        plans.py                   # PlanLimits dataclass, PLAN_LIMITS dict, Stripe price ID init
      config.py                    # Pydantic settings from environment
      database.py                  # Async engine, session factory, get_db dependency
      main.py                      # FastAPI app creation, router registration, startup events
    tests/
      conftest.py                  # Test fixtures: client, db, setup_db, auth helpers
      test_auth.py                 # 10 auth tests
      test_content.py              # 13 content generation tests
      test_templates.py            # 17 template management tests
      test_images.py               # 12 image management tests
      test_billing.py              # 9 billing tests
      test_api_keys.py             # 5 API key tests
      test_health.py               # 1 health check test
    alembic/                       # Database migration scripts
    alembic.ini
    requirements.txt
  dashboard/
    src/
      service.config.ts            # Single source of truth: name, colors, fonts, nav, plans
      app/
        page.tsx                   # Dashboard home (overview)
        login/page.tsx             # Login page
        register/page.tsx          # Registration page
        content/page.tsx           # Content generation page (Generate)
        templates/page.tsx         # Template management page
        billing/page.tsx           # Billing and subscription page
        api-keys/page.tsx          # API key management page
        settings/page.tsx          # User settings page
      lib/
        api.ts                     # API client with fetch wrapper
        auth.ts                    # Auth helpers for client-side
        utils.ts                   # Utility functions
  landing/
    src/                           # Static landing page
  docs/
    README.md                      # Documentation index
    SETUP.md                       # Setup guide
    ARCHITECTURE.md                # This file
    API_REFERENCE.md               # API endpoint documentation
    TESTING.md                     # Test infrastructure guide
    QA_ENGINEER.md                 # QA checklists
    PROJECT_MANAGER.md             # Project overview
    END_USER.md                    # User guide
    IMPLEMENTATION_STEPS.md        # Build history
  README.md
  Makefile
  docker-compose.yml
```

---

## Database Schema

ContentForge uses 7 database tables with UUID primary keys and proper foreign key relationships.

### Tables

| Table | Model | Purpose |
|-------|-------|---------|
| `users` | `User` | User accounts with email, hashed password, plan tier |
| `api_keys` | `ApiKey` | SHA-256 hashed API keys with scopes |
| `subscriptions` | `Subscription` | Stripe subscription state (synced via webhooks) |
| `generation_jobs` | `GenerationJob` | Content generation job tracking (pending/processing/completed/failed) |
| `generated_content` | `GeneratedContent` | Individual content items (title, description, meta, keywords, bullets) |
| `image_jobs` | `ImageJob` | Image download/optimization tracking |
| `templates` | `Template` | System and custom content generation templates |

### Relationships

- `User` → `Subscription` (one-to-one)
- `User` → `ApiKey` (one-to-many)
- `User` → `GenerationJob` (one-to-many)
- `GenerationJob` → `GeneratedContent` (one-to-many, cascade delete)
- `GenerationJob` → `ImageJob` (one-to-many, cascade delete)
- `User` → `Template` (one-to-many, custom templates only)

### Cascade Deletes

- Deleting a `GenerationJob` cascades to all `GeneratedContent` and `ImageJob` records via SQLAlchemy `cascade="all, delete-orphan"`
- Deleting an `ImageJob` does NOT delete the parent job

---

## Key Design Decisions

### 1. Independent User Table Per Service

Each service (ContentForge, TrendScout, etc.) maintains its own `users` table. Users can sign up directly or be provisioned via the dropshipping platform's `/auth/provision` endpoint. This allows services to run standalone or integrated.

**Benefit:** Services remain independently deployable. No shared auth database required.

### 2. Plan Limits Enforced at API Layer

Plan quotas (generations/month, images/month) are checked in `content_service.py` before creating jobs. The `PLAN_LIMITS` dict in `constants/plans.py` is the single source of truth for tier limits.

**Benefit:** Centralized enforcement. Cannot be bypassed by clients. Easy to audit and update.

### 3. Mock Mode for AI and Stripe

When `ANTHROPIC_API_KEY` or `STRIPE_SECRET_KEY` are not set, the service operates in mock mode:
- Content generation produces realistic mock text via `generate_mock_content()`
- Stripe checkout creates subscriptions directly in the database without calling Stripe

**Benefit:** Full local development without external dependencies or API costs. Tests run in mock mode by default.

### 4. Config-Driven Dashboard

`service.config.ts` is the single source of truth for branding (name, colors, fonts), navigation, and plan tiers. Changing this file updates the entire dashboard appearance.

**Benefit:** Consistent branding across all UI components. Easy to rebrand or white-label.

### 5. API Key Authentication

API keys are hashed with SHA-256 before storage. The raw key is only returned once at creation time. The `key_prefix` (first 12 characters) is stored for identification in the UI. The `get_current_user_or_api_key` dependency supports both JWT and API key auth.

**Benefit:** Secure storage. Keys are not reversible. Supports both human (JWT) and programmatic (API key) access patterns.

### 6. Template System

System templates (Professional, Casual, Luxury, SEO-Focused) are seeded at startup via `template_seeder.py` and are read-only. Users create custom templates with their preferred tone, style, and content types. Templates control AI prompt parameters.

**Benefit:** Consistent starting point for all users. Custom templates enable brand voice matching.

### 7. Pricing Service

The `pricing_service.py` module provides standalone markup calculation with psychological rounding strategies (round_99, round_95, round_00, none). It is a pure utility with no database dependencies.

**Benefit:** Reusable across services. Easy to test in isolation.

### 8. Celery for Async Processing

Image processing and bulk content generation use Celery for async execution. Jobs are queued in Redis and processed by workers.

**Benefit:** Non-blocking API responses. Scalable processing (add more workers).

---

## Design System

The dashboard uses a config-driven design defined in `dashboard/src/service.config.ts`.

### Brand Colors

| Property | Value |
|----------|-------|
| **Primary Color** | Violet Purple -- `oklch(0.60 0.22 300)` / `#8b5cf6` |
| **Accent Color** | Soft Lavender -- `oklch(0.75 0.18 280)` / `#a78bfa` |

### Typography

| Property | Value |
|----------|-------|
| **Heading Font** | Clash Display (bold display font for creative/content branding) |
| **Body Font** | Satoshi (modern geometric sans for clean body text) |

### Navigation Items

The sidebar is driven by `serviceConfig.navigation`:

| Label | Route | Icon |
|-------|-------|------|
| Dashboard | `/` | LayoutDashboard |
| Generate | `/content` | Sparkles |
| Templates | `/templates` | FileText |
| Images | `/images` | Image |
| History | `/history` | Clock |
| API Keys | `/api-keys` | Key |
| Billing | `/billing` | CreditCard |
| Settings | `/settings` | Settings |

---

## Platform Event Webhook

Each service receives platform events from the dropshipping backend via `POST /api/v1/webhooks/platform-events`. Events are HMAC-SHA256 signed using `platform_webhook_secret`. The receiver verifies the signature and routes events to service-specific handlers.

**Supported events:**
- User provisioning
- Subscription state changes
- Plan upgrades/downgrades

**Benefit:** Enables dropshipping platform integration while keeping services decoupled.

---

## Service Ports

| Service | Port | Purpose |
|---------|------|---------|
| Backend API | 8102 | FastAPI REST API |
| Dashboard | 3102 | Next.js admin dashboard |
| Landing Page | 3202 | Next.js marketing site |
| PostgreSQL | 5502 | Database |
| Redis | 6402 | Cache and Celery broker |

**Port allocation pattern:** Each service uses a unique port range to avoid conflicts in the monorepo:
- Backend: 81XX
- Dashboard: 31XX
- Landing: 32XX
- PostgreSQL: 55XX
- Redis: 64XX

Where XX is the service number (02 for ContentForge).

---

*See also: [Setup](SETUP.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md) · [README](README.md)*
