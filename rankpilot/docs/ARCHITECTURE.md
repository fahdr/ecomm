# RankPilot Architecture

> Part of [RankPilot](README.md) documentation

This document covers the technical architecture, tech stack, project structure, database design, and key architectural decisions for RankPilot.

## Tech Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Backend API | FastAPI + SQLAlchemy 2.0 (async) | Python 3.12 | REST API, business logic |
| Database | PostgreSQL | 16 | Data persistence |
| Cache / Message Queue | Redis | 7 | Session storage, Celery broker |
| Task Queue | Celery | latest | Background job processing |
| Dashboard | Next.js (App Router) + Tailwind CSS | Next.js 16 | User interface |
| Landing Page | Next.js (static export) | Next.js 16 | Marketing site |
| ORM Migrations | Alembic | latest | Database schema versioning |
| Password Hashing | bcrypt | latest | Secure password storage |
| JWT Auth | python-jose / PyJWT | latest | Authentication tokens |
| HTTP Test Client | httpx + pytest-asyncio | latest | Integration testing |

## System Architecture

```
                +-------------------+
                |   Landing Page    |
                |  (Next.js, :3203) |
                +--------+----------+
                         |
                +--------v----------+
                |    Dashboard      |
                |  (Next.js, :3103) |
                +--------+----------+
                         |
                +--------v----------+
                |   Backend API     |
                | (FastAPI, :8103)  |
                +--------+----------+
                         |
          +--------------+--------------+
          |                             |
+---------v---------+        +----------v---------+
|   PostgreSQL 16   |        |     Redis 7        |
|     (:5503)       |        |    (:6403)         |
+-------------------+        +----+---------------+
                                  |
                            +-----v--------+
                            |   Celery     |
                            | (Background) |
                            +--------------+
```

## Project Structure

```
rankpilot/
├── README.md                          # Service overview
├── Makefile                           # Build, test, run targets
├── docker-compose.yml                 # Local dev orchestration
├── docs/                              # Documentation
│   ├── README.md                      # This directory index
│   ├── SETUP.md                       # Setup guide
│   ├── ARCHITECTURE.md                # This file
│   ├── API_REFERENCE.md              # API documentation
│   ├── TESTING.md                     # Testing guide
│   ├── QA_ENGINEER.md                 # QA verification guide
│   ├── PROJECT_MANAGER.md            # PM overview
│   ├── END_USER.md                    # User guide
│   └── IMPLEMENTATION_STEPS.md        # Build history
│
├── backend/
│   ├── Dockerfile                     # Backend container
│   ├── alembic/                       # Database migrations
│   │   ├── env.py                     # Alembic config
│   │   └── versions/                  # Migration scripts
│   ├── app/
│   │   ├── main.py                    # FastAPI app entry point
│   │   ├── config.py                  # Settings (env vars)
│   │   ├── database.py                # Async engine + session factory
│   │   ├── api/                       # Route handlers (13 files)
│   │   │   ├── __init__.py
│   │   │   ├── auth.py               # Register, login, refresh, profile, provision
│   │   │   ├── deps.py               # Dependency injection (JWT + API key auth)
│   │   │   ├── health.py             # GET /health
│   │   │   ├── sites.py              # Site CRUD + domain verification
│   │   │   ├── blog_posts.py         # Blog post CRUD + AI generation
│   │   │   ├── keywords.py           # Keyword tracking CRUD + rank refresh
│   │   │   ├── audits.py             # Run audit + list/get audit history
│   │   │   ├── schema.py             # JSON-LD schema CRUD + preview
│   │   │   ├── billing.py            # Plans, checkout, portal, overview
│   │   │   ├── api_keys.py           # API key create, list, revoke
│   │   │   ├── usage.py              # Usage reporting endpoint
│   │   │   └── webhooks.py           # Stripe webhook handler
│   │   ├── models/                    # SQLAlchemy models (10 files)
│   │   │   ├── base.py               # DeclarativeBase
│   │   │   ├── user.py               # User + PlanTier enum
│   │   │   ├── subscription.py       # Stripe subscription
│   │   │   ├── api_key.py            # API key (hashed)
│   │   │   ├── site.py               # Site (domain for SEO tracking)
│   │   │   ├── blog_post.py          # Blog post (AI-generated content)
│   │   │   ├── keyword.py            # Keyword tracking record
│   │   │   ├── seo_audit.py          # SEO audit result
│   │   │   ├── schema_config.py      # JSON-LD schema config
│   │   │   └── __init__.py           # Exports all models for Alembic
│   │   ├── schemas/                   # Pydantic schemas
│   │   │   ├── auth.py               # Auth request/response schemas
│   │   │   ├── billing.py            # Billing schemas
│   │   │   └── seo.py                # SEO domain schemas (sites, posts, keywords, audits, schema)
│   │   ├── services/                  # Business logic layer (8 files)
│   │   │   ├── auth_service.py        # Registration, login, JWT, API key auth
│   │   │   ├── billing_service.py     # Stripe checkout, portal, usage
│   │   │   ├── site_service.py        # Site CRUD + verification
│   │   │   ├── blog_service.py        # Blog post CRUD + AI content generation (mock)
│   │   │   ├── keyword_service.py     # Keyword CRUD + rank update (mock)
│   │   │   ├── audit_service.py       # Audit execution + scoring (mock)
│   │   │   └── schema_service.py      # JSON-LD generation + preview rendering
│   │   ├── constants/
│   │   │   └── plans.py               # Plan tier limits (PlanLimits dataclass)
│   │   ├── tasks/
│   │   │   └── celery_app.py          # Celery configuration
│   │   └── utils/
│   │       └── helpers.py             # Utility functions
│   └── tests/                         # Backend tests (8 test files)
│       ├── conftest.py                # Fixtures (client, db, auth_headers)
│       ├── test_auth.py               # 11 auth tests
│       ├── test_health.py             # 1 health test
│       ├── test_sites.py              # 20 site tests
│       ├── test_blog.py               # 25 blog post tests
│       ├── test_keywords.py           # 16 keyword tests
│       ├── test_audits.py             # 15 audit tests
│       ├── test_billing.py            # 10 billing tests
│       └── test_api_keys.py           # 5 API key tests
│
├── dashboard/
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   └── src/
│       ├── service.config.ts          # Branding, navigation, plans (single source of truth)
│       ├── lib/
│       │   ├── api.ts                 # HTTP client for backend
│       │   ├── auth.ts                # JWT token management
│       │   └── utils.ts               # Utility functions
│       ├── app/
│       │   ├── layout.tsx             # Root layout with fonts + shell
│       │   ├── page.tsx               # Dashboard home
│       │   ├── login/page.tsx         # Login page
│       │   ├── register/page.tsx      # Registration page
│       │   ├── sites/page.tsx         # Site management
│       │   ├── keywords/page.tsx      # Keyword tracking
│       │   ├── audits/page.tsx        # SEO audit history
│       │   ├── billing/page.tsx       # Subscription management
│       │   ├── api-keys/page.tsx      # API key management
│       │   └── settings/page.tsx      # Account settings
│       └── components/
│           ├── shell.tsx              # Layout shell wrapper
│           ├── sidebar.tsx            # Sidebar navigation
│           ├── top-bar.tsx            # Top bar
│           ├── motion.tsx             # Animation primitives
│           └── ui/                    # Reusable UI components (badge, button, card, dialog, input, skeleton)
│
└── landing/                           # Static marketing site (Next.js)
    └── src/app/page.tsx               # Landing page
```

## Database Schema

### Core Tables

| Table | Primary Model | Key Columns |
|-------|--------------|-------------|
| `users` | `User` | id, email, hashed_password, plan (PlanTier enum), stripe_customer_id, external_platform_id |
| `subscriptions` | `Subscription` | id, user_id, plan, status, stripe_subscription_id |
| `api_keys` | `ApiKey` | id, user_id, key_hash (SHA-256), key_prefix, scopes, is_active |

### SEO Domain Tables

| Table | Primary Model | Key Columns |
|-------|--------------|-------------|
| `sites` | `Site` | id, user_id, domain, sitemap_url, is_verified, verification_method, status, last_crawled |
| `blog_posts` | `BlogPost` | id, site_id, user_id, title, slug, content (TEXT), meta_description, keywords (ARRAY), status, word_count, published_at |
| `keyword_tracking` | `KeywordTracking` | id, site_id, keyword, current_rank, previous_rank, search_volume, difficulty, tracked_since, last_checked |
| `seo_audits` | `SeoAudit` | id, site_id, overall_score (0-100), issues (JSON), recommendations (JSON), pages_crawled |
| `schema_configs` | `SchemaConfig` | id, site_id, page_type, schema_json (JSON), is_active |

### Relationships

```
User (1) ──< (N) Site
    │           │
    │           ├──< (N) BlogPost
    │           ├──< (N) KeywordTracking
    │           ├──< (N) SeoAudit
    │           └──< (N) SchemaConfig
    │
    ├──< (N) Subscription
    └──< (N) ApiKey
```

### Cascade Delete Behavior

- **Delete User** → Cascades to all Sites, Subscriptions, ApiKeys
- **Delete Site** → Cascades to all BlogPosts, KeywordTracking, SeoAudits, SchemaConfigs
- **Delete Subscription** → No cascades
- **Delete ApiKey** → No cascades

## Key Architectural Decisions

### 1. Independent User Table

RankPilot maintains its own `users` table separate from the platform. Users can:
- Register directly via `/auth/register`
- Be provisioned from the platform via `/auth/provision`

The `external_platform_id` field links back to the platform for cross-service integration.

### 2. Denormalized Plan Field

The `User.plan` field stores the current subscription tier (Free, Pro, Enterprise) as a denormalized copy for fast lookups. This is updated whenever:
- A subscription is created (via Stripe checkout or mock)
- A subscription is updated (via Stripe webhook)
- A subscription is cancelled (via Stripe webhook)

**Rationale**: Avoids JOINs on every request that checks plan limits.

### 3. Dual Plan Limit Enforcement

RankPilot enforces two types of limits:
- **Primary (`max_items`)**: Blog posts per calendar month (resets monthly)
- **Secondary (`max_secondary`)**: Total keywords tracked (cumulative)

**Rationale**: Two monetization levers give users distinct reasons to upgrade.

### 4. Mock Implementations

Several features use mock implementations for MVP:

| Feature | Mock Behavior | Production Implementation |
|---------|--------------|--------------------------|
| Domain Verification | Always succeeds | DNS TXT, meta tag, or file verification |
| AI Blog Generation | Template-based content | Anthropic Claude API integration |
| Keyword Rank Tracking | Random ranks 1-100 | SerpAPI or DataForSEO integration |
| SEO Audits | Template issues/recommendations | Real site crawler (Screaming Frog API) |

**Rationale**: Reduces external dependencies during development while maintaining realistic data structures.

### 5. Cascade Deletes

Deleting a site removes all related data:
```python
# In site.py model
blog_posts = relationship("BlogPost", back_populates="site", cascade="all, delete-orphan")
keyword_trackings = relationship("KeywordTracking", back_populates="site", cascade="all, delete-orphan")
seo_audits = relationship("SeoAudit", back_populates="site", cascade="all, delete-orphan")
schema_configs = relationship("SchemaConfig", back_populates="site", cascade="all, delete-orphan")
```

**Rationale**: Clean data model, prevents orphaned records, simplifies user experience.

### 6. Config-Driven Dashboard

The entire dashboard UI is driven by `service.config.ts`:
- Branding (colors, fonts, service name)
- Navigation structure
- Plan features and pricing
- API URL configuration

**Rationale**: Single source of truth makes rebranding trivial, enforces consistency.

### 7. Sentinel Value Pattern

Update functions use `Ellipsis` (`...`) to distinguish "field not provided" from "set to None":

```python
async def update_site(
    db, site,
    domain=None,
    sitemap_url=...,  # Ellipsis = not provided, None = clear the value
    status=None,
):
    if sitemap_url is not ...:
        site.sitemap_url = sitemap_url
```

**Rationale**: Allows clients to explicitly clear optional fields via `null` without requiring separate "unset" operations.

### 8. Cross-Service Integration

Two dedicated endpoints enable platform integration:

**`POST /auth/provision`** -- Platform creates RankPilot user:
```python
{
  "email": "user@example.com",
  "password": "generated-password",
  "plan": "pro",
  "external_platform_id": "uuid",
  "external_store_id": "uuid"
}
# Returns API key for subsequent requests
```

**`GET /usage`** -- Platform polls usage metrics:
```python
# Headers: X-API-Key or Authorization: Bearer
# Returns: { "blog_posts_this_month": 5, "total_keywords": 42 }
```

**Rationale**: Enables unified billing dashboards in the platform while maintaining service independence.

## Design System

The dashboard uses a config-driven design system defined in `service.config.ts`:

### Colors

- **Primary**: Emerald Green -- `oklch(0.65 0.18 155)` / `#10b981`
- **Accent**: Light Green -- `oklch(0.72 0.15 140)` / `#34d399`

### Typography

- **Heading Font**: General Sans (clean, trustworthy)
- **Body Font**: Nunito Sans

### Navigation Structure

The sidebar is driven by the `navigation` array in `service.config.ts`:

| Label | Route | Icon |
|-------|-------|------|
| Dashboard | `/` | LayoutDashboard |
| Sites | `/sites` | Globe |
| Blog Posts | `/blog-posts` | FileText |
| Keywords | `/keywords` | Search |
| Audits | `/audits` | ClipboardCheck |
| Schema | `/schema` | Code |
| API Keys | `/api-keys` | Key |
| Billing | `/billing` | CreditCard |
| Settings | `/settings` | Settings |

## Platform Event Webhook

RankPilot receives platform events from the dropshipping backend via `POST /api/v1/webhooks/platform-events`. Events are HMAC-SHA256 signed using `platform_webhook_secret`. The receiver verifies the signature and routes events to service-specific handlers.

**Event Types:**
- `user.created` -- New user registered on platform
- `user.updated` -- User profile changed
- `store.created` -- New store created (could trigger site provisioning)
- `subscription.updated` -- Plan tier changed

**Rationale**: Enables real-time synchronization of user/store data between platform and services.

---

*See also: [Setup](SETUP.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
