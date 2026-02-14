# FlowSend -- Implementation Steps

This document records every implementation step taken to build FlowSend, from initial scaffolding to the final dashboard pages. Each step includes what was built, the specific steps completed, and how to verify correctness.

---

## Step 1: Template Scaffolding

### What was built
The FlowSend service was scaffolded from the shared service template, establishing the project structure, configuration files, Docker setup, and boilerplate code for backend, dashboard, and landing page.

### Steps completed
1. Ran `scripts/create-service.sh` (or manual scaffold) to generate the FlowSend directory structure under `flowsend/`.
2. Configured `service.config.ts` with FlowSend-specific branding:
   - Name: "FlowSend", tagline: "Smart Email Marketing", slug: "flowsend"
   - API URL: `http://localhost:8104`
   - Primary color: Coral Red `oklch(0.65 0.20 25)` / `#f43f5e`
   - Accent color: Orange `oklch(0.75 0.18 40)` / `#fb923c`
   - Heading font: Satoshi, body font: Inter
3. Configured port assignments: backend 8104, dashboard 3104, landing 3204, PostgreSQL 5504, Redis 6404.
4. Set up `backend/app/config.py` with environment variable loading for DATABASE_URL, REDIS_URL, JWT_SECRET_KEY, Stripe keys.
5. Set up `backend/app/database.py` with async engine and session factory.
6. Set up `backend/app/main.py` as FastAPI entry point with CORS middleware and router registration.
7. Created `backend/alembic/` directory with Alembic configuration for database migrations.
8. Created `backend/requirements.txt` with all Python dependencies.
9. Created `dashboard/` with Next.js 16 App Router, Tailwind CSS, and Shadcn/ui component library.

### Verification
- `ls flowsend/` shows backend/, dashboard/, master-landing/ directories.
- `cat dashboard/src/service.config.ts` confirms FlowSend branding values.
- Backend starts without errors on port 8104.
- Dashboard starts without errors on port 3104.

---

## Step 2: Core Models -- User, Subscription, ApiKey

### What was built
The foundational database models shared across all services: user accounts, Stripe subscription tracking, and API keys for programmatic access.

### Steps completed
1. Created `backend/app/models/base.py` with SQLAlchemy declarative Base.
2. Created `backend/app/models/user.py`:
   - `PlanTier` enum (free, pro, enterprise)
   - `User` model with id, email, hashed_password, is_active, plan, stripe_customer_id, external_platform_id, external_store_id, created_at, updated_at
   - Relationships to Subscription and ApiKey
3. Created `backend/app/models/subscription.py`:
   - `SubscriptionStatus` enum (active, trialing, past_due, canceled, unpaid, incomplete)
   - `Subscription` model with Stripe subscription ID, price ID, plan tier, period dates, trial dates
   - Relationship back to User
4. Created `backend/app/models/api_key.py`:
   - `ApiKey` model with key_hash (SHA-256), key_prefix (first 8 chars), scopes (ARRAY), is_active, last_used_at, expires_at
   - Relationship back to User
5. Generated Alembic migration for these three tables.
6. Ran `alembic upgrade head` to create tables.

### Verification
- `alembic upgrade head` completes without errors.
- Tables `users`, `subscriptions`, `api_keys` exist in the database.
- All columns match the model definitions.

---

## Step 3: Contact and ContactList Models

### What was built
Contact management data models for storing email subscribers and organizing them into lists.

### Steps completed
1. Created `backend/app/models/contact.py`:
   - `Contact` model with user_id (FK), email (indexed), first_name, last_name, tags (PostgreSQL ARRAY(String)), custom_fields (JSON), is_subscribed (boolean), subscribed_at, unsubscribed_at, created_at, updated_at
   - Multi-tenant isolation via user_id FK with CASCADE delete
   - Relationship to User (owner)
2. Created `ContactList` model in the same file:
   - Fields: user_id (FK), name, description, list_type ("static" or "dynamic"), rules (JSON, for dynamic lists), contact_count (cached), created_at, updated_at
   - Relationship to User (owner)
3. Generated and applied Alembic migration for `contacts` and `contact_lists` tables.

### Verification
- Tables `contacts` and `contact_lists` exist with correct columns.
- `tags` column is PostgreSQL ARRAY type.
- `custom_fields` and `rules` columns are JSON type.

---

## Step 4: EmailTemplate Model

### What was built
Email template model supporting both system-provided and user-created templates.

### Steps completed
1. Created `backend/app/models/email_template.py`:
   - `EmailTemplate` model with user_id (nullable FK -- NULL for system templates), name, subject, html_content (Text), text_content (Text, optional), thumbnail_url, is_system (boolean), category (welcome/cart/promo/newsletter/transactional), created_at, updated_at
   - System templates (user_id=NULL) are accessible to all users but cannot be modified or deleted
2. Generated and applied Alembic migration for `email_templates` table.

### Verification
- Table `email_templates` exists with nullable `user_id` FK.
- `html_content` and `text_content` are Text columns (large content support).

---

## Step 5: Flow and FlowExecution Models

### What was built
Automated email sequence models with trigger configuration, step definitions, and per-contact execution tracking.

### Steps completed
1. Created `backend/app/models/flow.py`:
   - `Flow` model with user_id (FK), name, description, trigger_type (signup/purchase/abandoned_cart/custom/scheduled), trigger_config (JSON), status (draft/active/paused), steps (JSON list of step objects), stats (JSON cached metrics), created_at, updated_at
   - Relationships to User (owner) and FlowExecution (cascade delete)
2. Created `FlowExecution` model in the same file:
   - Fields: flow_id (FK), contact_id (FK), current_step (integer, 0-indexed), status (running/completed/failed/canceled), started_at, completed_at
   - Relationship back to Flow
3. Generated and applied Alembic migration for `flows` and `flow_executions` tables.

### Verification
- Tables `flows` and `flow_executions` exist with correct foreign keys.
- `steps` and `trigger_config` are JSON columns.
- CASCADE delete from flows removes flow_executions.

---

## Step 6: Campaign and EmailEvent Models

### What was built
Broadcast campaign model with denormalized metrics and individual email event tracking.

### Steps completed
1. Created `backend/app/models/campaign.py`:
   - `Campaign` model with user_id (FK), name, template_id (FK to email_templates, SET NULL on delete), list_id (FK to contact_lists, SET NULL on delete), subject, status (draft/scheduled/sending/sent/failed), scheduled_at, sent_at, total_recipients, sent_count, open_count, click_count, bounce_count, created_at, updated_at
   - Relationships to User, EmailTemplate, and EmailEvent (cascade delete)
2. Created `EmailEvent` model in the same file:
   - Fields: campaign_id (nullable FK), flow_id (nullable FK), contact_id (FK), event_type (sent/delivered/opened/clicked/bounced/unsubscribed), metadata (JSON), created_at
   - Indexed on campaign_id, flow_id, contact_id, and event_type for fast queries
   - Relationship back to Campaign
3. Generated and applied Alembic migration for `campaigns` and `email_events` tables.

### Verification
- Tables `campaigns` and `email_events` exist with correct foreign keys and indexes.
- Campaign has denormalized count columns (sent_count, open_count, etc.).
- EmailEvent has indexes on all FK columns and event_type.

---

## Step 7: Model Registry

### What was built
Central model registry that exports all models for Alembic migration detection.

### Steps completed
1. Updated `backend/app/models/__init__.py` to import and export all 10 models: Base, User, Subscription, ApiKey, Contact, ContactList, EmailTemplate, Flow, FlowExecution, Campaign, EmailEvent.
2. Updated `__all__` list to include all model names.

### Verification
- `from app.models import *` imports all models without errors.
- `alembic revision --autogenerate` detects no pending changes.

---

## Step 8: Plan Limits Configuration

### What was built
Plan tier definitions with resource limits enforced at the API layer.

### Steps completed
1. Created `backend/app/constants/plans.py`:
   - `PlanLimits` frozen dataclass with max_items (emails/month), max_secondary (contacts), price_monthly_cents, stripe_price_id, trial_days, api_access
   - `PLAN_LIMITS` dict mapping PlanTier to PlanLimits:
     - Free: 500 emails, 250 contacts, $0, no API access
     - Pro: 25,000 emails, 10,000 contacts, $39/mo, API access, 14-day trial
     - Enterprise: unlimited emails/contacts, $149/mo, API access, 14-day trial
   - `init_price_ids()` function for binding Stripe Price IDs at startup
   - `resolve_plan_from_price_id()` function for webhook processing

### Verification
- `PLAN_LIMITS[PlanTier.free].max_secondary == 250`
- `PLAN_LIMITS[PlanTier.enterprise].max_items == -1` (unlimited)

---

## Step 9: Service Layer Implementation

### What was built
Seven service modules containing all business logic, separated from the API route layer.

### Steps completed

#### 9a. Auth Service (`auth_service.py`)
- User registration with bcrypt password hashing
- Authentication (email + password verification)
- JWT token creation (access + refresh) and decoding
- User lookup by ID and by API key (SHA-256 hash matching)
- Cross-service user provisioning with API key generation

#### 9b. Contact Service (`contact_service.py`)
- `check_contact_limit()` -- enforces plan `max_secondary` limit
- `create_contact()` -- with duplicate email detection per user
- `get_contacts()` -- paginated with search (email ILIKE) and tag (ARRAY.any) filtering
- `get_contact()` / `update_contact()` / `delete_contact()` -- standard CRUD
- `import_contacts()` -- bulk import from email list or CSV, with deduplication and plan limit enforcement
- `create_contact_list()` / `get_contact_lists()` / `get_contact_list()` / `delete_contact_list()` -- contact list CRUD

#### 9c. Flow Service (`flow_service.py`)
- `create_flow()` -- creates in draft status
- `get_flows()` -- paginated with status filter
- `update_flow()` -- only allows draft or paused (raises ValueError for active)
- `activate_flow()` -- transitions to active (requires at least one step)
- `pause_flow()` -- transitions to paused (must be active)
- `delete_flow()` -- removes flow and cascades to executions
- `get_flow_executions()` -- paginated execution listing

#### 9d. Campaign Service (`campaign_service.py`)
- `create_campaign()` -- creates as draft (or scheduled if `scheduled_at` provided)
- `get_campaigns()` -- paginated with status filter
- `update_campaign()` -- only draft/scheduled campaigns
- `delete_campaign()` -- only draft/scheduled (raises ValueError for sent)
- `send_campaign_mock()` -- creates EmailEvent records for all subscribed contacts, updates denormalized counts
- `get_campaign_events()` -- paginated events with event_type filter

#### 9e. Template Service (`template_service.py`)
- `create_template()` -- creates custom template (is_system=False)
- `get_templates()` -- returns user's custom + system templates, with category filter
- `get_template()` -- returns own or system template
- `update_template()` -- only custom templates (raises ValueError for system)
- `delete_template()` -- only custom templates (raises ValueError for system)

#### 9f. Analytics Service (`analytics_service.py`)
- `get_aggregate_analytics()` -- computes totals across all campaigns (sent, opens, clicks, bounces), calculates rates with `_safe_rate()` for division-by-zero safety, includes per-campaign breakdown for sent campaigns
- `get_campaign_analytics()` -- per-campaign metrics with rates

#### 9g. Billing Service (`billing_service.py`)
- `create_subscription_checkout()` -- Stripe checkout session (mock mode creates subscription directly)
- `create_portal_session()` -- Stripe customer portal
- `get_subscription()` / `get_billing_overview()` -- subscription and usage data
- `get_usage()` -- usage metrics for cross-service integration
- `sync_subscription_from_event()` -- webhook handler for subscription lifecycle events

### Verification
- All service functions have comprehensive docstrings with Args, Returns, and Raises.
- Service layer is fully decoupled from the HTTP layer (no HTTPException or FastAPI imports).

---

## Step 10: API Route Layer

### What was built
13 FastAPI route modules mapping HTTP endpoints to service functions with authentication, validation, and error handling.

### Steps completed
1. **`api/deps.py`**: Authentication dependencies
   - `get_current_user` -- JWT Bearer token extraction and validation
   - `get_current_user_or_api_key` -- dual auth (JWT first, then X-API-Key fallback)

2. **`api/auth.py`**: 6 endpoints -- register, login, refresh, profile, forgot-password, provision

3. **`api/contacts.py`**: 10 endpoints -- contact CRUD (create, list, count, get, update, delete), import, contact list CRUD (create, list, delete)

4. **`api/flows.py`**: 9 endpoints -- flow CRUD (create, list, get, update, delete), activate, pause, list executions

5. **`api/campaigns.py`**: 8 endpoints -- campaign CRUD (create, list, get, update, delete), send, analytics, events

6. **`api/templates.py`**: 5 endpoints -- template CRUD (create, list, get, update, delete)

7. **`api/analytics.py`**: 1 endpoint -- aggregate analytics

8. **`api/billing.py`**: 5 endpoints -- list plans (public), checkout, portal, current subscription, overview

9. **`api/api_keys.py`**: 3 endpoints -- create, list, revoke

10. **`api/usage.py`**: 1 endpoint -- usage metrics (dual auth)

11. **`api/webhooks.py`**: 1 endpoint -- Stripe webhook handler

12. **`api/health.py`**: 1 endpoint -- health check

13. **`api/__init__.py`**: Router registry, mounts all sub-routers under `/api/v1/`

### Verification
- `GET http://localhost:8104/docs` shows all 35+ endpoints in Swagger UI.
- All endpoints are grouped by tags (auth, contacts, flows, campaigns, templates, analytics, billing, api-keys, usage, webhooks, health).

---

## Step 11: Test Suite

### What was built
87 comprehensive backend tests across 8 test files, covering all API endpoints, business logic, and edge cases.

### Steps completed
1. **`tests/conftest.py`**: Test infrastructure
   - Async test database with NullPool
   - Autouse `setup_db` fixture: CREATE ALL before tests, terminate connections + TRUNCATE CASCADE after each test
   - `client` fixture (unauthenticated AsyncClient)
   - `auth_headers` fixture (registered user with JWT)
   - `register_and_login()` helper function

2. **`tests/test_auth.py`** (11 tests): Register success/duplicate/short-password, login success/wrong-password/nonexistent, refresh success/access-token-fails, profile, unauthenticated

3. **`tests/test_contacts.py`** (22 tests): Create full/minimal/invalid-email/duplicate, list empty/pagination/search/tag-filter, get/update/unsubscribe/delete, count, import email-list/dedup/csv, contact lists create/dynamic/list/delete/not-found, auth requirement

4. **`tests/test_flows.py`** (24 tests): Create full/minimal/all-trigger-types/missing-name/missing-trigger, list empty/pagination/status-filter, get/update-draft/update-not-found/delete, activate-with-steps/without-steps/not-found, pause-active/draft-rejected/not-found, update-active-rejected/update-paused/reactivate, executions empty/not-found, auth requirement

5. **`tests/test_campaigns.py`** (21 tests): Create draft/scheduled/validation, list empty/pagination/status-filter, get/update-draft/update-not-found/delete-draft/delete-not-found, send/send-not-found/send-already-sent/delete-sent-rejected, analytics/analytics-not-found, events/events-not-found, auth requirement

6. **`tests/test_templates.py`** (18 tests): Create full/minimal/missing-fields/empty-name, list empty/pagination/category-filter, get/get-not-found, update/partial-update/update-not-found, delete/delete-not-found, auth requirement

7. **`tests/test_billing.py`** (9 tests): List plans/pricing, checkout pro/free-fails/duplicate-fails, overview/overview-after-subscribe, current-subscription-none/after-subscribe

8. **`tests/test_api_keys.py`** (5 tests): Create key, list keys, revoke key, auth via API key, invalid API key

9. **`tests/test_health.py`** (1 test): Health check returns 200

### Verification
- `pytest -v` shows 87 tests passing.
- No test depends on another test's state (full isolation via TRUNCATE).
- All tests run in <30 seconds.

---

## Step 12: Dashboard Pages

### What was built
9 feature pages and 2 auth pages for the FlowSend dashboard, built with Next.js 16, Tailwind CSS, Shadcn/ui, and motion animations.

### Steps completed

#### 12a. Dashboard Home (`app/page.tsx`)
- KPI cards: Current Plan, API Calls Used (with progress bar), API Keys
- Loading skeletons during data fetch
- Error state with retry button
- Quick action buttons (Create API Key, Manage Billing, View Settings)
- Animated counters and staggered reveal animations

#### 12b. Contacts Page (`app/contacts/page.tsx`)
- Searchable, paginated contact table with email, name, tags (badges), subscription status
- KPI cards: Total Contacts, Subscribed (on page), Unsubscribed (on page)
- Create Contact dialog (email, first name, last name, tags)
- Edit Contact dialog (all fields + subscription toggle switch)
- Import Contacts dialog (textarea for email list, tags, import result display)
- Delete confirmation dialog
- Debounced search (300ms)
- Pagination controls (Previous, Page X of Y, Next)
- Empty state with call-to-action buttons

#### 12c. Flows Page (`app/flows/page.tsx`)
- Flow list as card rows with status icon (color-coded), name, status badge, trigger label, step count
- KPI cards: Total Flows, Active, Drafts, Paused
- Status filter tabs: All, Draft, Active, Paused
- Create Flow dialog (name, description, trigger type select, steps JSON editor)
- Edit Flow dialog (same fields, pre-filled)
- Activate confirmation dialog
- Pause confirmation dialog
- Delete confirmation dialog
- Context-aware action buttons: Active shows Pause; Draft/Paused shows Edit, Activate, Delete
- Pagination controls and empty state

#### 12d. Campaigns Page (`app/campaigns/page.tsx`)
- Campaign list as card rows with status icon, name, badge, subject, sent/scheduled dates, delivered count
- KPI cards: Total Campaigns, Drafts, Sent
- Status filter tabs: All, Draft, Scheduled, Sent
- Create Campaign dialog (name, subject, optional schedule datetime)
- Edit Campaign dialog (name, subject)
- Send confirmation dialog
- Delete confirmation dialog
- Analytics dialog (total sent, opens with rate, clicks with rate, bounces with rate)
- Context-aware action buttons: Sent shows Analytics; Draft shows Edit, Send, Delete
- Pagination controls and empty state

#### 12e. Additional Pages
- **Billing** (`app/billing/page.tsx`): Plan cards, checkout flow, subscription display
- **API Keys** (`app/api-keys/page.tsx`): Key list, create dialog, revoke confirmation
- **Settings** (`app/settings/page.tsx`): Account settings
- **Login** (`app/login/page.tsx`): Email/password form with error handling
- **Register** (`app/register/page.tsx`): Registration form with validation

### Verification
- `npm run build` completes without errors for all 9 feature pages + 2 auth pages.
- All pages use the Shell layout (sidebar + top bar).
- All pages have loading skeletons, error states, and empty states.
- All interactive elements use confirmation dialogs for destructive actions.
- Navigation items in `service.config.ts` all route to real pages.

---

## Step 13: Landing Page

### What was built
A static marketing landing page for FlowSend at `master-landing/`.

### Steps completed
1. Created the landing page with FlowSend branding (Coral Red, Satoshi font).
2. Feature showcase sections covering contacts, flows, campaigns, templates, analytics.
3. Pricing section matching the three-tier plan structure.
4. Call-to-action buttons linking to the dashboard registration page.
5. Built as a static Next.js export for fast loading.

### Verification
- Landing page loads on port 3204.
- Pricing matches the plan tiers in `plans.py` and `service.config.ts`.
- Links to the dashboard registration page work correctly.

---

## Summary

| Step | Component | Artifacts | Test Count |
|------|-----------|-----------|------------|
| 1 | Scaffolding | Project structure, configs, Docker | -- |
| 2 | User/Sub/ApiKey models | 3 models, migration | -- |
| 3 | Contact/ContactList models | 2 models, migration | -- |
| 4 | EmailTemplate model | 1 model, migration | -- |
| 5 | Flow/FlowExecution models | 2 models, migration | -- |
| 6 | Campaign/EmailEvent models | 2 models, migration | -- |
| 7 | Model registry | __init__.py | -- |
| 8 | Plan limits | plans.py (PlanLimits dataclass) | -- |
| 9 | Service layer | 7 service modules | -- |
| 10 | API routes | 13 route modules, 35+ endpoints | -- |
| 11 | Test suite | 8 test files | **87 tests** |
| 12 | Dashboard | 9 feature pages + 2 auth pages | -- |
| 13 | Landing page | 1 static page | -- |
| **Total** | | **10+ tables, 35+ endpoints, 11+ pages** | **87 tests** |
