# AdScale Architecture

> Part of [AdScale](README.md) documentation

This document describes the technical architecture, database schema, design decisions, and system design of the AdScale AI Ad Campaign Manager service.

---

## Tech Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Backend API | FastAPI | Latest | REST API with async request handling |
| ORM | SQLAlchemy 2.0 (async) | 2.x | Database models and queries |
| Database | PostgreSQL | 16 | Persistent data storage |
| Cache / Queue Broker | Redis | 7 | Caching and Celery task queue |
| Task Queue | Celery | Latest | Background job processing |
| Dashboard | Next.js (App Router) | 16 | React-based admin dashboard |
| Dashboard Styling | Tailwind CSS | Latest | Utility-first CSS framework |
| Landing Page | Next.js (static) | 16 | Marketing site |
| Migrations | Alembic | Latest | Database schema versioning |
| Auth | JWT (access + refresh tokens) + API Key (SHA-256 hashed) | | User and service authentication |
| Testing | pytest + pytest-asyncio + httpx | Latest | Backend test suite |

---

## Project Structure

```
adscale/
├── README.md                       # Service overview
├── Makefile                        # Build automation
├── docker-compose.yml              # Container orchestration
├── docs/                           # Documentation
│   ├── README.md                   # Documentation hub (you are here)
│   ├── SETUP.md                    # Setup and installation
│   ├── ARCHITECTURE.md             # Architecture (this file)
│   ├── API_REFERENCE.md            # API documentation
│   ├── TESTING.md                  # Testing guide
│   ├── QA_ENGINEER.md              # QA checklists
│   ├── PROJECT_MANAGER.md          # PM overview
│   ├── END_USER.md                 # User guide
│   └── IMPLEMENTATION_STEPS.md     # Implementation history
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── config.py               # Environment-based settings
│   │   ├── database.py             # SQLAlchemy async engine + session
│   │   ├── api/                    # API route modules
│   │   │   ├── __init__.py         # Router aggregation
│   │   │   ├── deps.py             # Auth dependency injection
│   │   │   ├── auth.py             # Register, login, refresh, profile
│   │   │   ├── accounts.py         # Ad account connect/list/disconnect
│   │   │   ├── campaigns.py        # Campaign CRUD with plan limits
│   │   │   ├── ad_groups.py        # Ad group CRUD with plan limits
│   │   │   ├── creatives.py        # Creative CRUD + AI copy generation
│   │   │   ├── metrics.py          # Performance metrics endpoints
│   │   │   ├── rules.py            # Optimization rule CRUD + execute
│   │   │   ├── billing.py          # Stripe subscription management
│   │   │   ├── api_keys.py         # API key create/list/revoke
│   │   │   ├── usage.py            # Cross-service usage reporting
│   │   │   ├── health.py           # Health check
│   │   │   └── webhooks.py         # Stripe webhooks + platform events
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── __init__.py         # Model exports for Alembic
│   │   │   ├── base.py             # Declarative base
│   │   │   ├── user.py             # User + PlanTier enum
│   │   │   ├── subscription.py     # Stripe subscription tracking
│   │   │   ├── api_key.py          # SHA-256 hashed API keys
│   │   │   ├── ad_account.py       # AdAccount + platform/status enums
│   │   │   ├── campaign.py         # Campaign + objective/status enums
│   │   │   ├── ad_group.py         # AdGroup + bid strategy/status enums
│   │   │   ├── ad_creative.py      # AdCreative + approval status enum
│   │   │   ├── campaign_metrics.py # Daily performance metrics
│   │   │   └── optimization_rule.py# Optimization rule + type enum
│   │   ├── services/               # Business logic layer
│   │   │   ├── auth_service.py     # User registration, JWT, API key auth
│   │   │   ├── account_service.py  # Ad account connect/disconnect
│   │   │   ├── campaign_service.py # Campaign CRUD + plan limit checks
│   │   │   ├── creative_service.py # Creative CRUD + AI copy generation
│   │   │   ├── metrics_service.py  # ROAS, CPA, CTR aggregation
│   │   │   ├── optimization_service.py # Rule evaluation engine
│   │   │   └── billing_service.py  # Stripe checkout, portal, usage
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   │   ├── auth.py             # Auth schemas
│   │   │   ├── ads.py              # Ad account, campaign, ad group, creative, metrics, rule schemas
│   │   │   └── billing.py          # Plan, subscription, usage schemas
│   │   ├── constants/
│   │   │   └── plans.py            # Plan tier limits + Stripe binding
│   │   ├── utils/
│   │   │   └── helpers.py          # Shared utility functions
│   │   └── tasks/
│   │       └── celery_app.py       # Celery task definitions
│   ├── tests/                      # 164 backend tests
│   │   ├── conftest.py             # Fixtures: client, DB, auth helpers
│   │   ├── test_auth.py            # 11 tests: register, login, refresh
│   │   ├── test_accounts.py        # 15 tests: connect, list, disconnect
│   │   ├── test_campaigns.py       # 20 tests: CRUD, pagination, limits
│   │   ├── test_creatives.py       # 16 tests: CRUD, AI generation
│   │   ├── test_rules.py           # 20+ tests: CRUD, execute-now
│   │   ├── test_billing.py         # 9 tests: plans, checkout, overview
│   │   ├── test_api_keys.py        # 5 tests: create, list, revoke, auth
│   │   └── test_health.py          # 1 test: health check
│   └── alembic/                    # Database migrations
├── dashboard/
│   ├── src/
│   │   ├── service.config.ts       # Single source of truth (name, colors, nav, plans)
│   │   ├── app/                    # Next.js App Router pages
│   │   │   ├── layout.tsx          # Root layout with sidebar + top bar
│   │   │   ├── page.tsx            # Dashboard home (overview)
│   │   │   ├── campaigns/page.tsx  # Campaign management
│   │   │   ├── creatives/page.tsx  # Creative management
│   │   │   ├── analytics/page.tsx  # Performance analytics
│   │   │   ├── billing/page.tsx    # Billing + subscription
│   │   │   ├── api-keys/page.tsx   # API key management
│   │   │   ├── settings/page.tsx   # User settings
│   │   │   ├── login/page.tsx      # Login page
│   │   │   └── register/page.tsx   # Registration page
│   │   ├── lib/
│   │   │   ├── api.ts              # Typed API client with token management
│   │   │   ├── auth.ts             # Auth context + hooks
│   │   │   └── utils.ts            # Utility functions
│   │   └── components/
│   │       ├── sidebar.tsx          # Config-driven sidebar navigation
│   │       ├── top-bar.tsx          # Header bar with user menu
│   │       ├── shell.tsx            # Page shell wrapper
│   │       ├── motion.tsx           # Animation primitives
│   │       └── ui/                  # Reusable UI components
│   └── next.config.ts
└── landing/
    ├── src/
    │   ├── landing.config.ts       # Landing page configuration
    │   ├── app/
    │   │   ├── page.tsx            # Homepage
    │   │   ├── layout.tsx          # Root layout
    │   │   └── pricing/page.tsx    # Pricing page
    │   └── components/
    │       ├── hero.tsx            # Hero section
    │       ├── features.tsx        # Feature highlights
    │       ├── how-it-works.tsx    # How it works
    │       ├── pricing-cards.tsx   # Pricing tier cards
    │       ├── stats-bar.tsx       # Stats display
    │       ├── cta.tsx             # Call-to-action
    │       ├── navbar.tsx          # Navigation bar
    │       └── footer.tsx          # Footer
    └── next.config.ts
```

---

## Database Schema

### Core Tables

#### users
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| email | String(255) | Unique, indexed |
| hashed_password | String(255) | Not null |
| plan | PlanTier enum | Default: free |
| created_at | DateTime | Default: now() |

#### subscriptions
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | UUID | FK -> users.id, unique |
| stripe_customer_id | String(255) | Nullable |
| stripe_subscription_id | String(255) | Nullable, unique |
| plan_tier | PlanTier enum | Not null |
| status | String(50) | Not null |
| current_period_start | DateTime | Nullable |
| current_period_end | DateTime | Nullable |
| created_at | DateTime | Default: now() |

#### api_keys
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | UUID | FK -> users.id |
| key_hash | String(255) | Unique, indexed (SHA-256 hash) |
| name | String(100) | Not null |
| is_active | Boolean | Default: true |
| created_at | DateTime | Default: now() |

### AdScale-Specific Tables

#### ad_accounts
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | UUID | FK -> users.id |
| platform | AdPlatform enum | google, meta |
| account_id_external | String(255) | External account ID |
| account_name | String(255) | Not null |
| access_token_enc | Text | Nullable (encrypted OAuth token) |
| is_connected | Boolean | Default: true |
| status | AccountStatus enum | active, paused, error |
| connected_at | DateTime | Default: now() |
| created_at | DateTime | Default: now() |

**Unique constraint:** `(user_id, platform, account_id_external)` -- prevents duplicate connections

#### campaigns
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | UUID | FK -> users.id, indexed |
| ad_account_id | UUID | FK -> ad_accounts.id |
| name | String(255) | Not null |
| platform | AdPlatform enum | Denormalized from ad_account |
| objective | CampaignObjective enum | traffic, conversions, awareness, sales |
| budget_daily | Float | Nullable |
| budget_lifetime | Float | Nullable |
| status | CampaignStatus enum | draft, active, paused, completed |
| start_date | Date | Nullable |
| end_date | Date | Nullable |
| created_at | DateTime | Default: now() |
| updated_at | DateTime | Default: now(), on update |

#### ad_groups
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| campaign_id | UUID | FK -> campaigns.id |
| name | String(255) | Not null |
| targeting | JSON | Nullable (audience targeting parameters) |
| bid_strategy | BidStrategy enum | manual, auto_cpc, target_roas, maximize_conversions |
| bid_amount | Float | Nullable |
| status | AdGroupStatus enum | active, paused |
| created_at | DateTime | Default: now() |
| updated_at | DateTime | Default: now(), on update |

#### ad_creatives
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| ad_group_id | UUID | FK -> ad_groups.id |
| headline | String(255) | Not null |
| description | Text | Not null |
| image_url | String(512) | Nullable |
| destination_url | String(512) | Not null |
| call_to_action | String(50) | Default: "Shop Now" |
| status | CreativeStatus enum | active, paused, rejected |
| created_at | DateTime | Default: now() |
| updated_at | DateTime | Default: now(), on update |

#### campaign_metrics
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| campaign_id | UUID | FK -> campaigns.id, indexed |
| date | Date | Indexed |
| impressions | Integer | Default: 0 |
| clicks | Integer | Default: 0 |
| conversions | Integer | Default: 0 |
| spend | Float | Default: 0.0 |
| revenue | Float | Default: 0.0 |
| roas | Float | Nullable (pre-computed: revenue / spend) |
| cpa | Float | Nullable (pre-computed: spend / conversions) |
| ctr | Float | Nullable (pre-computed: clicks / impressions * 100) |
| created_at | DateTime | Default: now() |

**Unique constraint:** `(campaign_id, date)` -- one metrics row per campaign per day

#### optimization_rules
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | UUID | FK -> users.id, indexed |
| name | String(255) | Not null |
| rule_type | RuleType enum | pause_low_roas, scale_high_roas, adjust_bid, increase_budget |
| conditions | JSON | Nullable (arbitrary rule conditions) |
| threshold | Float | Not null |
| is_active | Boolean | Default: true |
| last_executed | DateTime | Nullable |
| executions_count | Integer | Default: 0 |
| created_at | DateTime | Default: now() |

---

## Design Decisions

### Ownership Model (Cascading Resources)

Resources form a strict hierarchical ownership chain:

```
User
├── Ad Account
│   └── Campaign
│       ├── Ad Group
│       │   └── Creative
│       └── Metrics
└── Optimization Rule
```

**Ownership validation:**
- Ad accounts validated directly via `ad_account.user_id == current_user.id`
- Campaigns validated via `campaign.user_id == current_user.id`
- Ad groups validated via `ad_group.campaign.user_id == current_user.id`
- Creatives validated via `creative.ad_group.campaign.user_id == current_user.id`
- Rules validated via `rule.user_id == current_user.id`

All `GET`, `PATCH`, `DELETE` operations verify ownership before returning or modifying data. This prevents resource access across user boundaries.

### Soft Disconnect for Ad Accounts

Ad accounts use **soft disconnect** instead of hard delete:
- Disconnecting sets `is_connected=False`, `status=paused`, clears `access_token_enc`
- Campaign history is preserved even after disconnection
- Allows reconnection with the same external account ID

**Rationale:** Ad campaigns often need historical data for reporting and optimization even after the account is disconnected.

### Denormalized `platform` Field in Campaigns

The `platform` field is denormalized from `ad_account.platform` into `campaigns.platform` to avoid joins during filtering and reporting queries.

**Tradeoff:** Requires updating campaign.platform if ad account platform changes (unlikely in practice).

### Pre-Computed Metrics (ROAS, CPA, CTR)

`campaign_metrics` stores pre-computed ROAS, CPA, and CTR values to avoid repeated calculations during dashboard rendering.

**Computation:**
- `roas = revenue / spend` (nullable if spend == 0)
- `cpa = spend / conversions` (nullable if conversions == 0)
- `ctr = (clicks / impressions) * 100` (nullable if impressions == 0)

**Rationale:** Dashboard performance is critical -- fetching raw metrics and computing in-app would slow down analytics pages.

### JSON Storage for Targeting and Conditions

`ad_groups.targeting` and `optimization_rules.conditions` use JSON fields for flexibility:
- Allows platform-specific targeting options (Google vs. Meta) without schema changes
- Supports arbitrary rule conditions for future rule types

**Tradeoff:** Querying JSON fields is slower than indexed columns, but these fields are not queried in filters (only read/write).

### Plan Limit Enforcement

Plan limits are enforced at the **service layer** (not database constraints):
- `campaign_service.check_campaign_limit()` checks before creating campaigns
- `ad_groups.py` route checks ad group count before creating ad groups

**Rationale:** Plan limits are business logic, not data integrity constraints. Database constraints would require schema changes for every plan adjustment.

### Optimization Rule Execution Engine

The `optimization_service.evaluate_and_execute()` function:
1. Fetches all active campaigns for the user
2. Retrieves last 7 days of metrics for each campaign
3. Calculates average ROAS
4. Applies rule type logic (pause, scale, adjust, increase)
5. Returns `campaigns_affected` count and `actions_taken` list

**Design:** Rules are evaluated on-demand via the `/rules/{id}/execute` endpoint. Future enhancement: scheduled evaluation via Celery Beat.

---

## API Conventions

### Authentication

All endpoints except `/auth/register`, `/auth/login`, `/billing/plans`, and `/health` require authentication.

**Supported methods:**
- **JWT Bearer:** `Authorization: Bearer <access_token>`
- **API Key:** `X-API-Key: <raw_key>` (for programmatic access)

**Dual Auth:** `/usage` and `/auth/provision` accept both JWT and API key.

### Request/Response Patterns

| Operation | Method | Status | Body | Response |
|-----------|--------|--------|------|----------|
| Create | POST | 201 | JSON | Created resource |
| List | GET | 200 | Query params | `PaginatedResponse { items, total, offset, limit }` |
| Get | GET | 200 | None | Resource or 404 |
| Update | PATCH | 200 | Partial JSON | Updated resource |
| Delete | DELETE | 204 | None | No body (or 404) |

### Error Codes

| Code | Meaning |
|------|---------|
| 400 | Invalid request data or UUID format |
| 401 | Missing or invalid authentication |
| 403 | Plan limit reached |
| 404 | Resource not found or not owned by current user |
| 409 | Conflict (duplicate resource) |
| 422 | Validation error (Pydantic) |

---

## Design System

The AdScale dashboard uses a config-driven design system centered on amber gold tones and clean typography.

| Property | Value |
|----------|-------|
| **Primary Color** | Amber Gold -- `oklch(0.72 0.18 80)` / `#f59e0b` |
| **Accent Color** | Light Amber -- `oklch(0.78 0.15 60)` / `#fbbf24` |
| **Heading Font** | Anybody |
| **Body Font** | Manrope |
| **Icon Library** | lucide-react |

**Configuration:**
All branding, colors, fonts, and navigation are defined in `/dashboard/src/service.config.ts`. Changing values in this file updates the entire dashboard UI.

---

## Platform Event Webhook

AdScale receives platform events from the dropshipping backend via `POST /api/v1/webhooks/platform-events`. Events are HMAC-SHA256 signed using `platform_webhook_secret`. The receiver verifies the signature and routes events to service-specific handlers.

**Event types:**
- `user.provisioned` -- Create or link user from platform
- `subscription.updated` -- Sync subscription status changes
- `usage.reset` -- Reset usage counters for billing period

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
