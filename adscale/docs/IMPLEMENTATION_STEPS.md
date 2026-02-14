# Implementation Steps

This document details how the AdScale service was implemented, step by step, from template scaffolding through models, services, routes, tests, dashboard pages, and landing page. It serves as both a historical record and a reference for building future services using the same architecture.

---

## Phase 1: Template Scaffolding

The AdScale service was scaffolded from the shared service template using `scripts/create-service.sh`. The scaffold script performed the following:

1. **Copied the template directory** into `services/adscale/`
2. **Replaced all template placeholders** with AdScale-specific values:
   - `{{SERVICE_NAME}}` -> `AdScale`
   - `{{SERVICE_SLUG}}` -> `adscale`
   - `{{SERVICE_TAGLINE}}` -> `AI Ad Campaign Manager`
   - `{{BACKEND_PORT}}` -> `8107`
   - `{{DASHBOARD_PORT}}` -> `3107`
   - `{{LANDING_PORT}}` -> `3207`
   - `{{DB_PORT}}` -> `5507`
   - `{{REDIS_PORT}}` -> `6407`
   - `{{PRIMARY_COLOR_OKLCH}}` -> `oklch(0.72 0.18 80)`
   - `{{PRIMARY_COLOR_HEX}}` -> `#f59e0b`
   - `{{ACCENT_COLOR_OKLCH}}` -> `oklch(0.78 0.15 60)`
   - `{{ACCENT_COLOR_HEX}}` -> `#fbbf24`
   - `{{HEADING_FONT}}` -> `Inter Tight`
   - `{{BODY_FONT}}` -> `Inter`
3. **Generated initial files:**
   - `backend/app/main.py` -- FastAPI app with CORS, router registration
   - `backend/app/config.py` -- Settings from environment variables
   - `backend/app/database.py` -- Async SQLAlchemy engine and session
   - `backend/app/api/deps.py` -- JWT and API key auth dependencies
   - `backend/app/api/auth.py` -- Register, login, refresh, profile, provision
   - `backend/app/api/health.py` -- Health check endpoint
   - `backend/app/api/billing.py` -- Plans, checkout, portal, subscription
   - `backend/app/api/api_keys.py` -- API key CRUD
   - `backend/app/api/usage.py` -- Cross-service usage reporting
   - `backend/app/api/webhooks.py` -- Stripe webhook handler
   - `backend/app/models/base.py` -- SQLAlchemy declarative base
   - `backend/app/models/user.py` -- User model with PlanTier enum
   - `backend/app/models/subscription.py` -- Stripe subscription model
   - `backend/app/models/api_key.py` -- API key model (SHA-256 hashed)
   - `backend/app/services/auth_service.py` -- User registration, JWT, API key lookup
   - `backend/app/services/billing_service.py` -- Stripe checkout, portal, usage
   - `backend/app/schemas/auth.py` -- Auth request/response schemas
   - `backend/app/schemas/billing.py` -- Billing schemas
   - `backend/app/constants/plans.py` -- Plan tier stub (limits to be customized)
   - `backend/tests/conftest.py` -- Test fixtures
   - `backend/tests/test_auth.py` -- Auth endpoint tests
   - `backend/tests/test_health.py` -- Health check test
   - `dashboard/src/service.config.ts` -- Service configuration stub
   - `dashboard/src/app/layout.tsx` -- Root layout
   - `dashboard/src/app/page.tsx` -- Dashboard home stub
   - `landing/src/app/page.tsx` -- Landing page stub

---

## Phase 2: Domain Models

### Step 2.1: Ad Account Model (`backend/app/models/ad_account.py`)

Created the `AdAccount` model to represent connected external advertising platform accounts:

- **Table:** `ad_accounts`
- **Fields:** `id` (UUID PK), `user_id` (FK -> users), `platform` (AdPlatform enum: google, meta), `account_id_external` (platform account ID), `account_name`, `access_token_enc` (encrypted OAuth token), `is_connected` (bool), `status` (AccountStatus enum: active, paused, error), `connected_at`, `created_at`
- **Enums:** `AdPlatform` (google, meta), `AccountStatus` (active, paused, error)
- **Relationships:** `user` (many-to-one -> User), `campaigns` (one-to-many -> Campaign, cascade delete-orphan)
- **Design decision:** Soft disconnect (set `is_connected=False`, `status=paused`, clear token) rather than hard delete to preserve campaign history

### Step 2.2: Campaign Model (`backend/app/models/campaign.py`)

Created the `Campaign` model for advertising campaigns:

- **Table:** `campaigns`
- **Fields:** `id` (UUID PK), `user_id` (FK -> users), `ad_account_id` (FK -> ad_accounts), `name`, `platform` (denormalized from ad_account), `objective` (CampaignObjective enum), `budget_daily` (float, nullable), `budget_lifetime` (float, nullable), `status` (CampaignStatus enum), `start_date`, `end_date`, `created_at`, `updated_at`
- **Enums:** `CampaignObjective` (traffic, conversions, awareness, sales), `CampaignStatus` (draft, active, paused, completed)
- **Relationships:** `ad_account` (many-to-one -> AdAccount), `ad_groups` (one-to-many -> AdGroup, cascade delete-orphan), `metrics` (one-to-many -> CampaignMetrics, cascade delete-orphan)
- **Design decision:** `platform` denormalized from ad_account for query performance; campaigns are the primary billable resource (`max_items` plan limit)

### Step 2.3: Ad Group Model (`backend/app/models/ad_group.py`)

Created the `AdGroup` model for organizing ads within campaigns:

- **Table:** `ad_groups`
- **Fields:** `id` (UUID PK), `campaign_id` (FK -> campaigns), `name`, `targeting` (JSON dict for audience parameters), `bid_strategy` (BidStrategy enum), `bid_amount` (float, nullable), `status` (AdGroupStatus enum), `created_at`, `updated_at`
- **Enums:** `BidStrategy` (manual, auto_cpc, target_roas, maximize_conversions), `AdGroupStatus` (active, paused)
- **Relationships:** `campaign` (many-to-one -> Campaign), `creatives` (one-to-many -> AdCreative, cascade delete-orphan)
- **Design decision:** `targeting` stored as JSON for flexibility (age, gender, interests, locations); ad groups are the secondary billable resource (`max_secondary` plan limit)

### Step 2.4: Ad Creative Model (`backend/app/models/ad_creative.py`)

Created the `AdCreative` model for individual ad units:

- **Table:** `ad_creatives`
- **Fields:** `id` (UUID PK), `ad_group_id` (FK -> ad_groups), `headline` (255 chars), `description` (1024 chars), `image_url` (nullable), `destination_url`, `call_to_action` (50 chars, default "Shop Now"), `status` (CreativeStatus enum), `created_at`, `updated_at`
- **Enums:** `CreativeStatus` (active, paused, rejected)
- **Relationships:** `ad_group` (many-to-one -> AdGroup)
- **Design decision:** `rejected` status for platform policy violations; headline limited to 255 chars to match most ad platform requirements

### Step 2.5: Campaign Metrics Model (`backend/app/models/campaign_metrics.py`)

Created the `CampaignMetrics` model for daily performance tracking:

- **Table:** `campaign_metrics`
- **Fields:** `id` (UUID PK), `campaign_id` (FK -> campaigns), `date` (indexed), `impressions` (int), `clicks` (int), `conversions` (int), `spend` (float), `revenue` (float), `roas` (float, nullable), `cpa` (float, nullable), `ctr` (float, nullable), `created_at`
- **Relationships:** `campaign` (many-to-one -> Campaign)
- **Design decision:** ROAS, CPA, and CTR are pre-computed during metric sync for fast dashboard queries; nullable to handle division-by-zero cases (no spend, no impressions, no conversions)

### Step 2.6: Optimization Rule Model (`backend/app/models/optimization_rule.py`)

Created the `OptimizationRule` model for automated campaign management:

- **Table:** `optimization_rules`
- **Fields:** `id` (UUID PK), `user_id` (FK -> users), `name`, `rule_type` (RuleType enum), `conditions` (JSON dict), `threshold` (float), `is_active` (bool), `last_executed` (datetime, nullable), `executions_count` (int), `created_at`
- **Enums:** `RuleType` (pause_low_roas, scale_high_roas, adjust_bid, increase_budget)
- **Relationships:** `user` (many-to-one -> User)
- **Design decision:** Rules are user-scoped (not campaign-scoped) so one rule can apply across all campaigns; `executions_count` tracks usage for analytics

### Step 2.7: Model Registration (`backend/app/models/__init__.py`)

Registered all models in `__init__.py` so Alembic can auto-detect them:

```python
__all__ = [
    "Base", "User", "Subscription", "ApiKey",
    "AdAccount", "Campaign", "AdGroup", "AdCreative",
    "CampaignMetrics", "OptimizationRule",
]
```

---

## Phase 3: Service Layer

### Step 3.1: Account Service (`backend/app/services/account_service.py`)

Implemented ad account business logic:

- `connect_account()` -- Creates an AdAccount record with duplicate detection (same external ID + platform + user); mock OAuth token if not provided
- `list_accounts()` -- Paginated listing scoped to user
- `get_account()` -- Single account retrieval with user ownership check
- `disconnect_account()` -- Soft disconnect: sets `is_connected=False`, `status=paused`, clears access token

### Step 3.2: Campaign Service (`backend/app/services/campaign_service.py`)

Implemented campaign CRUD with plan limit enforcement:

- `check_campaign_limit()` -- Counts non-completed campaigns against `PLAN_LIMITS[user.plan].max_items`; raises `ValueError` if limit reached
- `create_campaign()` -- Validates ad account ownership, checks plan limit, auto-sets platform from ad account
- `list_campaigns()` -- Paginated listing scoped to user
- `get_campaign()` -- Single retrieval with ownership check
- `update_campaign()` -- Partial update (only non-None fields)
- `delete_campaign()` -- Hard delete with cascade (SQLAlchemy handles ad groups/creatives/metrics)
- `count_campaigns()` -- Utility for billing usage reporting

### Step 3.3: Creative Service (`backend/app/services/creative_service.py`)

Implemented creative CRUD and AI copy generation:

- `create_creative()` -- Validates ad group exists, creates creative with all fields
- `list_creatives()` -- Paginated listing with optional ad_group_id filter
- `get_creative()` -- Single retrieval by ID
- `update_creative()` -- Partial update
- `delete_creative()` -- Hard delete
- `generate_ad_copy()` -- Mock AI implementation: generates deterministic headline, description, and CTA based on product info; varies CTA by tone ("professional" -> "Learn More", "urgent" -> "Buy Now", etc.)

### Step 3.4: Metrics Service (`backend/app/services/metrics_service.py`)

Implemented metrics aggregation and querying:

- `get_campaign_metrics()` -- Per-campaign daily metrics with optional date range filter and pagination
- `get_metrics_overview()` -- Cross-campaign aggregation: totals for spend/revenue/impressions/clicks/conversions, averages for ROAS/CTR/CPA; division-by-zero protection returns `None` for computed fields when denominator is 0
- `get_metrics_by_date_range()` -- All metrics within a date range across all user campaigns, ordered by date ascending (for time-series charts)

### Step 3.5: Optimization Service (`backend/app/services/optimization_service.py`)

Implemented rule CRUD and execution engine:

- `create_rule()` -- Creates an optimization rule with type, conditions JSON, and threshold
- `list_rules()` / `get_rule()` / `update_rule()` / `delete_rule()` -- Standard CRUD scoped to user
- `evaluate_and_execute()` -- The rule execution engine:
  1. Fetches the rule and validates ownership
  2. Gets all active campaigns for the user
  3. For each campaign, retrieves last 7 days of metrics and calculates average ROAS
  4. Evaluates the rule type against the threshold:
     - `pause_low_roas`: Pauses campaign if ROAS < threshold
     - `scale_high_roas`: Increases daily budget by 20% if ROAS > threshold
     - `adjust_bid`: Flags bid adjustment needed if ROAS < threshold
     - `increase_budget`: Increases daily budget by 15% if ROAS > threshold
  5. Updates `last_executed` and increments `executions_count`
  6. Returns `rule_id`, `campaigns_affected` count, and `actions_taken` descriptions

---

## Phase 4: API Routes

### Step 4.1: Ad Account Routes (`backend/app/api/accounts.py`)

- `POST /api/v1/accounts` -- Connect ad account (201 / 409 duplicate)
- `GET /api/v1/accounts` -- List accounts with `offset`/`limit` pagination
- `DELETE /api/v1/accounts/{account_id}` -- Disconnect account (204 / 404)
- All endpoints require JWT auth via `get_current_user` dependency

### Step 4.2: Campaign Routes (`backend/app/api/campaigns.py`)

- `POST /api/v1/campaigns` -- Create campaign with plan limit check (201 / 403 / 400)
- `GET /api/v1/campaigns` -- List campaigns (paginated)
- `GET /api/v1/campaigns/{campaign_id}` -- Get by ID (200 / 404)
- `PATCH /api/v1/campaigns/{campaign_id}` -- Partial update, converts enum values
- `DELETE /api/v1/campaigns/{campaign_id}` -- Delete with cascade (204 / 404)

### Step 4.3: Ad Group Routes (`backend/app/api/ad_groups.py`)

- `POST /api/v1/ad-groups` -- Create with campaign ownership validation and plan limit check (201 / 403 / 400)
- `GET /api/v1/ad-groups` -- List with optional `campaign_id` query filter
- `GET /api/v1/ad-groups/{ad_group_id}` -- Get by ID with ownership validation through campaign
- `PATCH /api/v1/ad-groups/{ad_group_id}` -- Partial update
- `DELETE /api/v1/ad-groups/{ad_group_id}` -- Delete with cascade to creatives
- Ownership validation: ad groups are validated through `campaign.user_id == current_user.id`

### Step 4.4: Creative Routes (`backend/app/api/creatives.py`)

- `POST /api/v1/creatives` -- Create with full chain ownership validation (400 if ad group not owned)
- `GET /api/v1/creatives` -- List with optional `ad_group_id` filter
- `GET /api/v1/creatives/{creative_id}` -- Get by ID with ownership check
- `PATCH /api/v1/creatives/{creative_id}` -- Partial update with ownership check
- `DELETE /api/v1/creatives/{creative_id}` -- Delete with ownership check
- `POST /api/v1/creatives/generate-copy` -- AI copy generation (product_name, product_description, target_audience, tone)
- Ownership chain: `creative.ad_group_id -> ad_group.campaign_id -> campaign.user_id`

### Step 4.5: Metrics Routes (`backend/app/api/metrics.py`)

- `GET /api/v1/metrics/overview` -- Aggregated overview with optional `start_date`/`end_date` query params
- `GET /api/v1/metrics/campaign/{campaign_id}` -- Per-campaign daily metrics (paginated, max 365 items)
- `GET /api/v1/metrics/date-range` -- Date range query (required `start_date` and `end_date`)

### Step 4.6: Optimization Rule Routes (`backend/app/api/rules.py`)

- `POST /api/v1/rules` -- Create rule (201)
- `GET /api/v1/rules` -- List rules (paginated)
- `GET /api/v1/rules/{rule_id}` -- Get by ID (200 / 404)
- `PATCH /api/v1/rules/{rule_id}` -- Partial update, converts enum values
- `DELETE /api/v1/rules/{rule_id}` -- Delete (204 / 404)
- `POST /api/v1/rules/{rule_id}/execute` -- Execute-now endpoint: evaluates rule against active campaigns and returns execution result

### Step 4.7: Router Registration (`backend/app/api/__init__.py`)

Registered all routers under the `/api/v1` prefix in the main app:

```python
# Standard (from template)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(billing_router, prefix="/api/v1")
app.include_router(api_keys_router, prefix="/api/v1")
app.include_router(usage_router, prefix="/api/v1")
app.include_router(webhooks_router, prefix="/api/v1")

# AdScale-specific
app.include_router(accounts_router, prefix="/api/v1")
app.include_router(campaigns_router, prefix="/api/v1")
app.include_router(ad_groups_router, prefix="/api/v1")
app.include_router(creatives_router, prefix="/api/v1")
app.include_router(metrics_router, prefix="/api/v1")
app.include_router(rules_router, prefix="/api/v1")
```

---

## Phase 5: Schemas (`backend/app/schemas/ads.py`)

Created Pydantic schemas for all domain entities:

- **AdAccountConnect** -- Request: platform, account_id_external, account_name, access_token (optional)
- **AdAccountResponse** -- Response: all fields + id, user_id, is_connected, status, connected_at
- **CampaignCreate** -- Request: ad_account_id, name, objective (enum), budget_daily, budget_lifetime, status (enum), start_date, end_date
- **CampaignUpdate** -- Request: all optional (partial update)
- **CampaignResponse** -- Response: all fields + id, user_id, platform, created_at, updated_at
- **AdGroupCreate** -- Request: campaign_id, name, targeting (dict), bid_strategy, bid_amount, status
- **AdGroupUpdate** -- Request: all optional
- **AdGroupResponse** -- Response: all fields + id, created_at, updated_at
- **CreativeCreate** -- Request: ad_group_id, headline, description, destination_url, image_url, call_to_action, status
- **CreativeUpdate** -- Request: all optional
- **CreativeResponse** -- Response: all fields + id, created_at, updated_at
- **GenerateCopyRequest** -- Request: product_name, product_description, target_audience (optional), tone (optional)
- **GenerateCopyResponse** -- Response: headline, description, call_to_action
- **MetricsOverview** -- Response: total_spend, total_revenue, total_impressions, total_clicks, total_conversions, avg_roas, avg_ctr, avg_cpa
- **MetricsResponse** -- Response: all metric fields + id, campaign_id, date, created_at
- **RuleCreate** -- Request: name, rule_type (enum), conditions (dict), threshold, is_active
- **RuleUpdate** -- Request: all optional
- **RuleResponse** -- Response: all fields + id, user_id, last_executed, executions_count, created_at
- **RuleExecutionResult** -- Response: rule_id, campaigns_affected, actions_taken (list)
- **PaginatedResponse** -- Generic wrapper: items (list), total, offset, limit

---

## Phase 6: Plan Configuration (`backend/app/constants/plans.py`)

Customized the plan limits for AdScale:

| Tier | max_items (campaigns) | max_secondary (ad groups) | price_monthly_cents | trial_days | api_access |
|------|----------------------|--------------------------|--------------------:|------------|------------|
| free | 2 | 5 | 0 | 0 | False |
| pro | 25 | 100 | 4900 | 14 | True |
| enterprise | -1 (unlimited) | -1 (unlimited) | 14900 | 14 | True |

---

## Phase 7: Tests

### Step 7.1: Test Infrastructure (`backend/tests/conftest.py`)

- Async engine with `NullPool` for test isolation
- `setup_db` autouse fixture: creates tables before test, terminates all non-self DB connections and truncates all tables after each test
- `override_get_db` overrides the database dependency for the test session
- `register_and_login()` helper registers a user and returns auth headers
- `client` fixture provides `httpx.AsyncClient` configured for the FastAPI app
- `auth_headers` fixture provides pre-authenticated headers

### Step 7.2: Auth Tests (`backend/tests/test_auth.py`) -- 11 tests

Register success, duplicate email (409), short password (422), login success, wrong password (401), nonexistent user (401), token refresh, wrong token type for refresh (401), profile access, profile unauthenticated (401).

### Step 7.3: Account Tests (`backend/tests/test_accounts.py`) -- 15 tests

Connect Google/Meta, duplicate (409), same ID different platform, unauthenticated (401), list empty/with data/pagination, user isolation, disconnect success (204)/not found (404)/invalid UUID (400)/other user (404).

### Step 7.4: Campaign Tests (`backend/tests/test_campaigns.py`) -- 20 tests

Create success/all objectives/lifetime budget/unauthenticated, list empty/with data/pagination/user isolation, get by ID/not found/invalid UUID, update name/budget/status/objective/not found, delete success/not found/other user/invalid UUID.

### Step 7.5: Creative Tests (`backend/tests/test_creatives.py`) -- 16 tests

Uses `_setup_chain()` helper to create full account -> campaign -> ad group chain. Create success/custom CTA/invalid ad group/unauthenticated, list empty/with data/filter by ad group/user isolation, get by ID/not found/invalid UUID, update headline/status/not found, delete success/not found/other user, AI copy generation/minimal fields/unauthenticated.

### Step 7.6: Rule Tests (`backend/tests/test_rules.py`) -- 20+ tests

Create success/all types/inactive/custom conditions/unauthenticated, list empty/with data/pagination/user isolation, get by ID/not found/invalid UUID/other user, update name/threshold/deactivate/type/conditions/not found, delete success/not found/other user/invalid UUID, execute-now no campaigns/not found/invalid UUID/unauthenticated.

### Step 7.7: Billing Tests (`backend/tests/test_billing.py`) -- 9 tests

List plans (3 tiers), pricing details, checkout Pro (201), checkout Free (400), duplicate subscription (400), billing overview, overview after subscribe, current subscription none/after subscribe.

### Step 7.8: API Key Tests (`backend/tests/test_api_keys.py`) -- 5 tests

Create key (raw key returned), list keys (no raw keys), revoke key, auth via X-API-Key, invalid API key (401).

### Step 7.9: Health Test (`backend/tests/test_health.py`) -- 1 test

Health check returns status, service name, timestamp.

**Total: 77 backend tests across 8 test files.**

---

## Phase 8: Dashboard Pages

### Step 8.1: Service Configuration (`dashboard/src/service.config.ts`)

Configured the single source of truth for the dashboard:

- **Name:** "AdScale", **Tagline:** "AI Ad Campaign Manager", **Slug:** "adscale"
- **API URL:** `http://localhost:8107` (configurable via `NEXT_PUBLIC_API_URL`)
- **Colors:** Primary `oklch(0.72 0.18 80)` / `#f59e0b`, Accent `oklch(0.78 0.15 60)` / `#fbbf24`
- **Fonts:** Heading "Inter Tight", Body "Inter"
- **Navigation:** 9 items (Dashboard, Campaigns, Ad Groups, Creatives, Rules, Analytics, API Keys, Billing, Settings)
- **Plans:** 3 tiers (Free $0, Pro $49, Enterprise $149) with feature lists

### Step 8.2: Dashboard Pages

Created 9 dashboard pages:

| Page | Route | Purpose |
|------|-------|---------|
| Dashboard Home | `/` | Overview with key metrics summary |
| Campaigns | `/campaigns` | Campaign list and management |
| Creatives | `/creatives` | Creative management and AI generation |
| Analytics | `/analytics` | Performance metrics and charts |
| Billing | `/billing` | Plan management and subscription |
| API Keys | `/api-keys` | API key management |
| Settings | `/settings` | User settings and ad account connections |
| Login | `/login` | User login form |
| Register | `/register` | New user registration form |

### Step 8.3: Shared Components

- **Sidebar** (`components/sidebar.tsx`) -- Config-driven navigation from `service.config.ts`
- **Top Bar** (`components/top-bar.tsx`) -- Header with user menu
- **Shell** (`components/shell.tsx`) -- Page wrapper with sidebar + top bar
- **Motion** (`components/motion.tsx`) -- Animation primitives for transitions
- **UI Components** (`components/ui/`) -- Button, Card, Input, Dialog, Badge, Skeleton

---

## Phase 9: Landing Page

Created 2 landing pages with 7 components:

| Component | Purpose |
|-----------|---------|
| Hero | Main headline, tagline, CTA button |
| Features | Feature highlights grid |
| How It Works | Step-by-step explanation |
| Stats Bar | Key statistics display |
| Pricing Cards | 3-tier pricing comparison |
| CTA | Bottom call-to-action section |
| Navbar / Footer | Navigation and footer |

**Pages:**
- `/` -- Homepage with hero, features, how-it-works, stats, CTA
- `/pricing` -- Dedicated pricing page with detailed tier comparison

---

## Summary

| Phase | Items Created | Key Files |
|-------|-------------|-----------|
| 1. Scaffolding | Project skeleton | main.py, config.py, database.py, auth, billing, deps |
| 2. Models | 6 domain models + __init__ | ad_account.py, campaign.py, ad_group.py, ad_creative.py, campaign_metrics.py, optimization_rule.py |
| 3. Services | 5 service modules | account_service.py, campaign_service.py, creative_service.py, metrics_service.py, optimization_service.py |
| 4. Routes | 6 route modules | accounts.py, campaigns.py, ad_groups.py, creatives.py, metrics.py, rules.py |
| 5. Schemas | 1 comprehensive schema file | ads.py (17+ schema classes) |
| 6. Plans | 1 config file | plans.py (3 tiers) |
| 7. Tests | 8 test files, 77 tests | test_auth, test_accounts, test_campaigns, test_creatives, test_rules, test_billing, test_api_keys, test_health |
| 8. Dashboard | 9 pages, 10+ components | page.tsx files + sidebar, shell, motion, UI components |
| 9. Landing | 2 pages, 7 components | hero, features, how-it-works, pricing-cards, stats-bar, cta, navbar, footer |
