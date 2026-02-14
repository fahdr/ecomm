# FlowSend -- Developer Guide

## Introduction

FlowSend is an independently hostable SaaS product for **Smart Email Marketing**. It provides a complete email marketing automation platform with contact management, visual email flow builders, broadcast campaigns, email template editing, A/B testing (Pro+), and delivery analytics. FlowSend can be used standalone or integrated with the dropshipping platform via the provisioning API.

**Notable:** FlowSend has the most complex data model of all services in the platform (10+ database tables) and the highest test count at **87 backend tests** across 8 test files. Feature logic is distributed across five dedicated service modules: `contact_service.py`, `flow_service.py`, `campaign_service.py`, `template_service.py`, and `analytics_service.py`. Flow execution runs via Celery tasks with step-by-step processing. The dashboard is config-driven via `dashboard/src/service.config.ts`.

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend API | FastAPI + SQLAlchemy 2.0 (async) | Python 3.12 |
| Database | PostgreSQL | 16 |
| Cache / Queue Broker | Redis | 7 |
| Task Queue | Celery | latest |
| Migrations | Alembic | latest |
| Dashboard | Next.js (App Router) + Tailwind CSS | 16 |
| Landing Page | Next.js (static export) | 16 |
| UI Components | Shadcn/ui | latest |
| Auth | JWT (access + refresh tokens) + API keys (SHA-256 hashed) |
| Billing | Stripe (mock mode in dev) |

---

## Local Development

### Ports

| Component | Port | URL |
|-----------|------|-----|
| Backend API | 8104 | http://localhost:8104 |
| API Docs (Swagger) | 8104 | http://localhost:8104/docs |
| Dashboard | 3104 | http://localhost:3104 |
| Landing Page | 3204 | http://localhost:3204 |
| PostgreSQL | 5504 | `postgresql://dropship:dropship_dev@localhost:5504/flowsend` |
| Redis | 6404 | `redis://localhost:6404/0` |

### Quick Start

```bash
make install     # Install Python + Node dependencies
make migrate     # Run Alembic migrations
make start       # Start backend, dashboard, and landing page
```

### Access Points

- **API**: http://localhost:8104
- **Swagger Docs**: http://localhost:8104/docs
- **Dashboard**: http://localhost:3104
- **Landing Page**: http://localhost:3204

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://dropship:dropship_dev@db:5504/flowsend` | Async database connection |
| `DATABASE_URL_SYNC` | `postgresql://dropship:dropship_dev@db:5504/flowsend` | Sync connection (Alembic) |
| `REDIS_URL` | `redis://redis:6404/0` | Redis cache |
| `CELERY_BROKER_URL` | `redis://redis:6404/1` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://redis:6404/2` | Celery results |
| `JWT_SECRET_KEY` | (generated) | Secret for JWT signing |
| `STRIPE_SECRET_KEY` | (empty = mock mode) | Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | (empty = mock mode) | Stripe webhook signature secret |
| `STRIPE_PRO_PRICE_ID` | (empty) | Stripe Price ID for Pro tier |
| `STRIPE_ENTERPRISE_PRICE_ID` | (empty) | Stripe Price ID for Enterprise tier |

---

## Project Structure

```
services/flowsend/
  backend/
    app/
      api/                    # FastAPI route modules
        __init__.py           # Router registry
        auth.py               # Registration, login, refresh, profile, provisioning
        contacts.py           # Contact CRUD + bulk import + contact lists
        flows.py              # Flow CRUD + activate/pause lifecycle + executions
        campaigns.py          # Campaign CRUD + send (mock) + analytics + events
        templates.py          # Email template CRUD (custom + system)
        analytics.py          # Aggregate analytics endpoint
        billing.py            # Plans, checkout, portal, subscription, overview
        api_keys.py           # API key create, list, revoke
        deps.py               # Auth dependencies (JWT + API key)
        health.py             # Health check endpoint
        usage.py              # Usage reporting for cross-service integration
        webhooks.py           # Stripe webhook handler
      constants/
        plans.py              # Plan tier definitions and limits (PlanLimits dataclass)
      models/
        __init__.py           # Model registry (exports all models for Alembic)
        base.py               # SQLAlchemy declarative base
        user.py               # User model + PlanTier enum
        subscription.py       # Subscription model + SubscriptionStatus enum
        api_key.py            # ApiKey model (SHA-256 hashed keys)
        contact.py            # Contact + ContactList models
        email_template.py     # EmailTemplate model (system + custom)
        flow.py               # Flow + FlowExecution models
        campaign.py           # Campaign + EmailEvent models
      schemas/
        auth.py               # Auth request/response schemas
        billing.py            # Billing request/response schemas
        email.py              # Contact, flow, campaign, template, analytics schemas
      services/
        auth_service.py       # User registration, authentication, JWT, provisioning
        billing_service.py    # Stripe checkout, portal, subscription sync, usage
        contact_service.py    # Contact CRUD, import, plan limit checks
        flow_service.py       # Flow CRUD, activate/pause lifecycle
        campaign_service.py   # Campaign CRUD, mock send, event creation
        template_service.py   # Template CRUD (custom + system read)
        analytics_service.py  # Aggregate + per-campaign analytics computation
      config.py               # Settings from environment variables
      database.py             # AsyncEngine + session factory
      main.py                 # FastAPI app entry point
    tests/
      conftest.py             # Test fixtures (client, db, auth helpers)
      test_auth.py            # 11 auth tests
      test_contacts.py        # 22 contact tests
      test_flows.py           # 24 flow tests
      test_campaigns.py       # 21 campaign tests
      test_templates.py       # 18 template tests
      test_billing.py         # 9 billing tests
      test_api_keys.py        # 5 API key tests
      test_health.py          # 1 health check test
    alembic/                  # Database migration scripts
    alembic.ini
    requirements.txt
  dashboard/
    src/
      app/
        page.tsx              # Dashboard home (KPI cards, quick actions)
        contacts/page.tsx     # Contact management (table, search, import, CRUD dialogs)
        flows/page.tsx        # Automation flows (list, status filter, lifecycle actions)
        campaigns/page.tsx    # Campaign management (list, send, analytics)
        billing/page.tsx      # Billing/subscription management
        api-keys/page.tsx     # API key management
        settings/page.tsx     # Account settings
        login/page.tsx        # Login page
        register/page.tsx     # Registration page
      components/
        shell.tsx             # Layout shell (sidebar + top bar)
        motion.tsx            # Animation components (FadeIn, StaggerChildren, etc.)
        ui/                   # Shadcn/ui components
      lib/
        api.ts                # API client with { data, error } envelope
        utils.ts              # Utility functions (cn, etc.)
      service.config.ts       # Service branding, navigation, plans (single source of truth)
  master-landing/             # Static landing page (Next.js)
```

---

## Database Tables

FlowSend has **10+ tables**, making it the most complex data model across all services:

| Table | Model | Purpose |
|-------|-------|---------|
| `users` | `User` | User accounts with plan tier, Stripe customer ID, external platform IDs |
| `subscriptions` | `Subscription` | Stripe subscription state (synced via webhooks) |
| `api_keys` | `ApiKey` | SHA-256 hashed API keys for programmatic access |
| `contacts` | `Contact` | Email contacts with tags (ARRAY), custom fields (JSON), subscription status |
| `contact_lists` | `ContactList` | Static or dynamic contact lists with rules (JSON) |
| `email_templates` | `EmailTemplate` | System (user_id=NULL) + custom email templates with HTML/text content |
| `flows` | `Flow` | Automated email sequences with trigger config, steps (JSON), lifecycle status |
| `flow_executions` | `FlowExecution` | Per-contact progress through a flow (current_step, status) |
| `campaigns` | `Campaign` | Broadcast email campaigns with denormalized send/open/click/bounce counts |
| `email_events` | `EmailEvent` | Individual delivery events (sent, delivered, opened, clicked, bounced, unsubscribed) |
| `unsubscribes` | -- | CAN-SPAM compliant unsubscribe records |

### Key Data Model Details

- **Contact.tags**: Uses PostgreSQL `ARRAY(String)` for fast tag-based filtering with `Contact.tags.any(tag)`.
- **Contact.custom_fields**: JSON column for flexible per-contact metadata.
- **Flow.steps**: JSON list of step objects, each with `type` (email/delay/condition), `config`, and index.
- **Flow.trigger_type**: One of `signup`, `purchase`, `abandoned_cart`, `custom`, `scheduled`.
- **Flow status lifecycle**: `draft` -> `active` -> `paused` -> `active` (re-activate).
- **Campaign status lifecycle**: `draft` -> `scheduled` -> `sending` -> `sent` (or `failed`).
- **EmailEvent.event_type**: One of `sent`, `delivered`, `opened`, `clicked`, `bounced`, `unsubscribed`.
- **Campaign denormalized counts**: `sent_count`, `open_count`, `click_count`, `bounce_count` are updated from EmailEvents for fast dashboard rendering.

---

## Testing

FlowSend has **87 backend tests** -- the highest test count of all services in the platform.

```bash
make test-backend    # Run all 87 tests
pytest -v            # Verbose output
pytest tests/test_contacts.py -v   # Run a single test file
```

### Test Distribution

| Test File | Count | Scope |
|-----------|-------|-------|
| `test_contacts.py` | 22 | Contact CRUD, import, lists, pagination, search, tags |
| `test_flows.py` | 24 | Flow CRUD, activate/pause lifecycle, executions, validation |
| `test_campaigns.py` | 21 | Campaign CRUD, send (mock), analytics, events, status transitions |
| `test_templates.py` | 18 | Template CRUD, category filter, system template protection |
| `test_auth.py` | 11 | Register, login, refresh, profile, duplicates, validation |
| `test_billing.py` | 9 | Plans listing, checkout, overview, subscription states |
| `test_api_keys.py` | 5 | Key creation, listing, revocation, API key auth |
| `test_health.py` | 1 | Health check endpoint |
| **Total** | **87** | |

### Test Infrastructure

- **Async**: All tests use `pytest-asyncio` with `httpx.AsyncClient`.
- **Isolation**: Tables are `TRUNCATE CASCADE`'d between tests; non-self DB connections are terminated to prevent deadlocks.
- **Fixtures**: `client` (unauthenticated), `auth_headers` (registered user with JWT), `db` (raw session).
- **Mock Stripe**: Tests run with empty `STRIPE_SECRET_KEY`, activating mock billing mode (subscriptions created directly, no real Stripe API calls).

---

## API Conventions

- **Base path**: `/api/v1/`
- **Auth**: `Authorization: Bearer <JWT>` or `X-API-Key: <key>` header
- **Pagination**: All list endpoints return `{ items, total, page, page_size }`
- **Status codes**: 201 (created), 200 (success), 204 (deleted, no content), 400 (business logic error), 401 (unauthenticated), 404 (not found), 409 (conflict), 422 (validation error)
- **Error format**: `{ "detail": "Human-readable error message" }`
- **DELETE responses**: Return 204 with no body. Dashboard `api.ts` must check `response.status === 204` before calling `.json()`.

### API Endpoint Summary

| Group | Endpoints | Key Operations |
|-------|-----------|----------------|
| Auth | `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/me`, `/auth/forgot-password`, `/auth/provision` | Register, login, token refresh, profile, cross-service provisioning |
| Contacts | `/contacts` (CRUD), `/contacts/count`, `/contacts/import`, `/contacts/lists` (CRUD) | Create, list (paginated + search + tag filter), update, delete, bulk import (email list + CSV), contact lists |
| Flows | `/flows` (CRUD), `/flows/{id}/activate`, `/flows/{id}/pause`, `/flows/{id}/executions` | Create (draft), list (status filter), update (draft/paused only), delete, activate (requires steps), pause, list executions |
| Campaigns | `/campaigns` (CRUD), `/campaigns/{id}/send`, `/campaigns/{id}/analytics`, `/campaigns/{id}/events` | Create (draft/scheduled), list (status filter), update (draft only), delete (draft only), send (mock), analytics, event list |
| Templates | `/templates` (CRUD) | Create custom, list (custom + system), update/delete (custom only), category filter |
| Analytics | `/analytics` | Aggregate analytics (totals, rates, per-campaign breakdown) |
| Billing | `/billing/plans`, `/billing/checkout`, `/billing/portal`, `/billing/current`, `/billing/overview` | List plans (public), create checkout, customer portal, current subscription, full billing overview |
| API Keys | `/api-keys` (create, list, revoke) | Create (returns raw key once), list (no raw keys), revoke (deactivate) |
| Usage | `/usage` | Cross-service usage reporting (JWT or API key auth) |
| Webhooks | `/webhooks/stripe` | Stripe subscription lifecycle events |
| Health | `/health` | Service health check |

---

## Design System

The FlowSend dashboard uses a distinctive Coral Red color scheme to differentiate it from other services.

| Element | Value |
|---------|-------|
| **Primary Color** | Coral Red -- `oklch(0.65 0.20 25)` / `#f43f5e` |
| **Accent Color** | Orange -- `oklch(0.75 0.18 40)` / `#fb923c` |
| **Heading Font** | Satoshi (friendly, approachable) |
| **Body Font** | Inter |
| **Color Mode** | OKLCH-based with hex fallbacks for non-OKLCH contexts |

The design system is defined in `dashboard/src/service.config.ts` as the single source of truth for all branding, navigation, and plan tiers. Changing `name`, `tagline`, `colors`, or `fonts` in this file updates the entire dashboard.

### Navigation Items

The sidebar navigation is driven by `serviceConfig.navigation`:

| Label | Route | Icon |
|-------|-------|------|
| Dashboard | `/` | LayoutDashboard |
| Flows | `/flows` | GitBranch |
| Campaigns | `/campaigns` | Megaphone |
| Contacts | `/contacts` | Users |
| Templates | `/templates` | LayoutTemplate |
| Analytics | `/analytics` | BarChart3 |
| API Keys | `/api-keys` | Key |
| Billing | `/billing` | CreditCard |
| Settings | `/settings` | Settings |

---

## Key Architecture Decisions

1. **Multi-tenant isolation**: All queries filter by `user_id`. Contacts, flows, campaigns, templates, and lists are all scoped to the authenticated user.
2. **Plan limit enforcement**: `check_contact_limit()` in `contact_service.py` checks `PLAN_LIMITS[user.plan].max_secondary` before creating contacts. Similar checks exist for flows and emails.
3. **Mock send**: `send_campaign_mock()` in `campaign_service.py` creates `EmailEvent` records for all subscribed contacts without actual email delivery. In production, this would queue Celery tasks.
4. **Denormalized campaign counts**: `Campaign.sent_count`, `open_count`, `click_count`, `bounce_count` are updated directly from EmailEvents for fast dashboard display without JOIN queries.
5. **API key auth**: Keys are hashed with SHA-256 before storage. The raw key is only returned once at creation time. The `key_prefix` (first 12 chars) is stored for identification.
6. **Cross-service provisioning**: The `/auth/provision` endpoint allows the dropshipping platform to create FlowSend users and receive API keys for integration.
7. **Config-driven dashboard**: All branding, navigation, and billing tiers are defined in `service.config.ts`, making the dashboard fully configurable for white-labeling.
