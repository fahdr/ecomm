# FlowSend Architecture

> Part of [FlowSend](README.md) documentation

This document describes FlowSend's technical architecture, including tech stack, project structure, database schema, key design decisions, and design system.

## Tech Stack

| Layer | Technology | Version | Notes |
|-------|-----------|---------|-------|
| Backend API | FastAPI + SQLAlchemy 2.0 (async) | Python 3.12 | Async I/O for high concurrency |
| Database | PostgreSQL | 16 | JSONB, ARRAY types for flexible data |
| Cache / Queue Broker | Redis | 7 | Used for cache and Celery |
| Task Queue | Celery | latest | Async email sending, flow execution |
| Migrations | Alembic | latest | Schema versioning |
| Dashboard | Next.js (App Router) + Tailwind CSS | 16 | Server components, streaming |
| Landing Page | Next.js (static export) | 16 | Fast, SEO-friendly |
| UI Components | Shadcn/ui | latest | Accessible, customizable |
| Auth | JWT (access + refresh) + API keys | -- | SHA-256 hashed API keys |
| Billing | Stripe (mock mode in dev) | -- | Webhooks for subscription sync |

## Project Structure

```
flowsend/
├── backend/
│   ├── app/
│   │   ├── api/                    # FastAPI route modules
│   │   │   ├── __init__.py         # Router registry
│   │   │   ├── auth.py             # Register, login, refresh, profile, provisioning
│   │   │   ├── contacts.py         # Contact CRUD + bulk import + lists
│   │   │   ├── flows.py            # Flow CRUD + activate/pause + executions
│   │   │   ├── campaigns.py        # Campaign CRUD + send + analytics + events
│   │   │   ├── templates.py        # Template CRUD (custom + system)
│   │   │   ├── analytics.py        # Aggregate analytics
│   │   │   ├── billing.py          # Plans, checkout, portal, subscription, overview
│   │   │   ├── api_keys.py         # API key create, list, revoke
│   │   │   ├── deps.py             # Auth dependencies (JWT + API key)
│   │   │   ├── health.py           # Health check
│   │   │   ├── usage.py            # Usage reporting for platform integration
│   │   │   └── webhooks.py         # Stripe webhook handler
│   │   ├── constants/
│   │   │   └── plans.py            # Plan tier definitions and limits
│   │   ├── models/
│   │   │   ├── __init__.py         # Model registry (all models exported)
│   │   │   ├── base.py             # SQLAlchemy declarative base
│   │   │   ├── user.py             # User model + PlanTier enum
│   │   │   ├── subscription.py     # Subscription model + status enum
│   │   │   ├── api_key.py          # ApiKey model (SHA-256 hashed)
│   │   │   ├── contact.py          # Contact + ContactList models
│   │   │   ├── email_template.py   # EmailTemplate model (system + custom)
│   │   │   ├── flow.py             # Flow + FlowExecution models
│   │   │   └── campaign.py         # Campaign + EmailEvent models
│   │   ├── schemas/
│   │   │   ├── auth.py             # Auth request/response schemas
│   │   │   ├── billing.py          # Billing request/response schemas
│   │   │   └── email.py            # Contact, flow, campaign, template, analytics schemas
│   │   ├── services/
│   │   │   ├── auth_service.py     # User auth, JWT, API key lookup, provisioning
│   │   │   ├── billing_service.py  # Stripe checkout, portal, subscription sync
│   │   │   ├── contact_service.py  # Contact CRUD, import, plan limit checks
│   │   │   ├── flow_service.py     # Flow CRUD, activate/pause lifecycle
│   │   │   ├── campaign_service.py # Campaign CRUD, mock send, event creation
│   │   │   ├── template_service.py # Template CRUD (custom + system read)
│   │   │   └── analytics_service.py# Aggregate + per-campaign analytics
│   │   ├── config.py               # Settings from environment variables
│   │   ├── database.py             # AsyncEngine + session factory
│   │   └── main.py                 # FastAPI app entry point
│   ├── tests/
│   │   ├── conftest.py             # Test fixtures (client, db, auth helpers)
│   │   ├── test_auth.py            # 11 auth tests
│   │   ├── test_contacts.py        # 22 contact tests
│   │   ├── test_flows.py           # 24 flow tests
│   │   ├── test_campaigns.py       # 21 campaign tests
│   │   ├── test_templates.py       # 18 template tests
│   │   ├── test_billing.py         # 9 billing tests
│   │   ├── test_api_keys.py        # 5 API key tests
│   │   └── test_health.py          # 1 health check test
│   ├── alembic/                    # Database migration scripts
│   ├── alembic.ini
│   └── requirements.txt
├── dashboard/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx            # Dashboard home (KPI cards, quick actions)
│   │   │   ├── contacts/page.tsx   # Contact management
│   │   │   ├── flows/page.tsx      # Automation flows
│   │   │   ├── campaigns/page.tsx  # Campaign management
│   │   │   ├── templates/page.tsx  # Template library
│   │   │   ├── analytics/page.tsx  # Analytics dashboard
│   │   │   ├── billing/page.tsx    # Billing/subscription
│   │   │   ├── api-keys/page.tsx   # API key management
│   │   │   ├── settings/page.tsx   # Account settings
│   │   │   ├── login/page.tsx      # Login page
│   │   │   └── register/page.tsx   # Registration page
│   │   ├── components/
│   │   │   ├── shell.tsx           # Layout shell (sidebar + top bar)
│   │   │   ├── motion.tsx          # Animation components
│   │   │   └── ui/                 # Shadcn/ui components
│   │   ├── lib/
│   │   │   ├── api.ts              # API client with { data, error } envelope
│   │   │   └── utils.ts            # Utility functions (cn, etc.)
│   │   └── service.config.ts       # Service branding, navigation, plans
│   └── tsconfig.json
└── landing/                        # Static landing page (Next.js)
```

## Database Schema

FlowSend has **10+ tables**, the most complex data model across all services:

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

**Contact.tags**
- Uses PostgreSQL `ARRAY(String)` for fast tag-based filtering with `Contact.tags.any(tag)`.

**Contact.custom_fields**
- JSON column for flexible per-contact metadata.

**Flow.steps**
- JSON list of step objects, each with `type` (email/delay/condition), `config`, and index.

**Flow.trigger_type**
- One of `signup`, `purchase`, `abandoned_cart`, `custom`, `scheduled`.

**Flow status lifecycle**
- `draft` → `active` → `paused` → `active` (re-activate).

**Campaign status lifecycle**
- `draft` → `scheduled` → `sending` → `sent` (or `failed`).

**EmailEvent.event_type**
- One of `sent`, `delivered`, `opened`, `clicked`, `bounced`, `unsubscribed`.

**Campaign denormalized counts**
- `sent_count`, `open_count`, `click_count`, `bounce_count` are updated from EmailEvents for fast dashboard rendering without JOIN queries.

### Entity Relationships

```
User (1) ──< (N) Contact
User (1) ──< (N) ContactList
User (1) ──< (N) EmailTemplate (custom)
User (1) ──< (N) Flow
User (1) ──< (N) Campaign
User (1) ──< (1) Subscription
User (1) ──< (N) ApiKey

Flow (1) ──< (N) FlowExecution
Flow (1) ──< (N) EmailEvent

Campaign (1) ──< (N) EmailEvent

Contact (1) ──< (N) FlowExecution
Contact (1) ──< (N) EmailEvent

EmailTemplate (1) ──< (N) Campaign
ContactList (1) ──< (N) Campaign
```

## Key Architecture Decisions

### 1. Multi-Tenant Isolation

All queries filter by `user_id`. Contacts, flows, campaigns, templates, and lists are all scoped to the authenticated user. No cross-user data leakage is possible.

### 2. Plan Limit Enforcement

`check_contact_limit()` in `contact_service.py` checks `PLAN_LIMITS[user.plan].max_secondary` before creating contacts. Similar checks exist for flows and emails. Limits are defined in `backend/app/constants/plans.py` as a `PlanLimits` dataclass.

### 3. Mock Send

`send_campaign_mock()` in `campaign_service.py` creates `EmailEvent` records for all subscribed contacts without actual email delivery. In production, this would queue Celery tasks for real email providers (SendGrid, SES, etc.).

### 4. Denormalized Campaign Counts

`Campaign.sent_count`, `open_count`, `click_count`, `bounce_count` are updated directly from EmailEvents for fast dashboard display without JOIN queries. This is a deliberate tradeoff: slightly stale counts (updated asynchronously) for fast page loads.

### 5. API Key Auth

Keys are hashed with SHA-256 before storage. The raw key is only returned once at creation time. The `key_prefix` (first 12 chars) is stored for identification in the UI. API key auth is supported via the `X-API-Key` header alongside JWT Bearer tokens.

### 6. Cross-Service Provisioning

The `/auth/provision` endpoint allows the dropshipping platform to create FlowSend users and receive API keys for integration. Users provisioned this way have `external_platform_id` and `external_store_id` fields linking them to their platform account.

### 7. Config-Driven Dashboard

All branding, navigation, and billing tiers are defined in `dashboard/src/service.config.ts`, making the dashboard fully configurable for white-labeling without code changes.

## Platform Event Webhook

Each service receives platform events from the dropshipping backend via `POST /api/v1/webhooks/platform-events`. Events are HMAC-SHA256 signed using `platform_webhook_secret`. The receiver verifies the signature and routes events to service-specific handlers.

## Design System

The FlowSend dashboard uses a distinctive **Coral Red** color scheme to differentiate it from other services.

| Element | Value | Notes |
|---------|-------|-------|
| **Primary Color** | Coral Red — `oklch(0.65 0.20 25)` / `#f43f5e` | Main brand color |
| **Accent Color** | Orange — `oklch(0.75 0.18 40)` / `#fb923c` | Highlights, CTAs |
| **Heading Font** | Satoshi | Friendly, approachable |
| **Body Font** | Source Sans 3 | Highly legible |
| **Color Mode** | OKLCH-based with hex fallbacks | Works in older browsers |

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

## Service Modules

FlowSend distributes business logic across **7 dedicated service modules**:

| Module | Responsibilities |
|--------|-----------------|
| `auth_service.py` | User registration, authentication, JWT token creation/validation, API key lookup, cross-service provisioning |
| `contact_service.py` | Contact CRUD, bulk import (email list + CSV), plan limit enforcement, contact lists |
| `flow_service.py` | Flow CRUD, activate/pause lifecycle, validation (e.g., reject activate if no steps) |
| `campaign_service.py` | Campaign CRUD, mock send with EmailEvent creation, event listing |
| `template_service.py` | Template CRUD for custom templates, read-only access to system templates |
| `analytics_service.py` | Aggregate analytics (totals, rates), per-campaign analytics |
| `billing_service.py` | Stripe checkout session creation, customer portal, subscription sync from webhooks, usage reporting |

This separation keeps API route handlers thin (validation, auth, HTTP concerns) and service modules focused on business logic (testable, reusable).

---

*See also: [Setup](SETUP.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md) · [README](README.md)*
