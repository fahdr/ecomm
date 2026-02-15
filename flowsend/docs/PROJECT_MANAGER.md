# FlowSend -- Project Manager Guide

> Part of [FlowSend](README.md) documentation

## Overview

FlowSend is the **Smart Email Marketing** service in the platform suite (Feature A4). It enables users to manage email contacts, build automated email sequences (flows), send broadcast campaigns, create reusable templates, and track delivery analytics. FlowSend can operate as a standalone SaaS product or as an integrated service within the dropshipping platform.

---

## Differentiators

| Differentiator | Detail |
|---------------|--------|
| **Most complex data model** | 10+ database tables across contacts, lists, templates, flows, executions, campaigns, events, and unsubscribes -- the largest schema of all services |
| **Highest test count** | 151 backend tests across 8 test files, ensuring comprehensive coverage of all features and edge cases |
| **CAN-SPAM compliant** | Built-in unsubscribe handling, subscription tracking, and contact opt-in/opt-out management |
| **Visual flow builder** | Automated email sequences with trigger-based activation (signup, purchase, abandoned cart, custom events, scheduled) |
| **Cross-service integration** | Provisioning API allows the dropshipping platform to create FlowSend accounts and manage them via API keys |
| **Config-driven dashboard** | All branding, navigation, and billing tiers are defined in a single configuration file for easy customization |

---

## Architecture

FlowSend follows a three-tier architecture with clear separation of concerns:

| Component | Technology | Port |
|-----------|-----------|------|
| Backend API | FastAPI + SQLAlchemy 2.0 (async) | 8104 |
| Dashboard | Next.js 16 + Tailwind CSS | 3104 |
| Landing Page | Next.js 16 (static) | 3204 |
| Database | PostgreSQL 16 | 5504 |
| Cache/Queue | Redis 7 | 6404 |
| Task Queue | Celery | -- |

### Data Flow

```
User -> Dashboard (Next.js) -> Backend API (FastAPI) -> PostgreSQL
                                      |
                                      v
                                Celery (Redis) -> Email Delivery (future)
```

---

## Current Status

| Metric | Value |
|--------|-------|
| Backend tests | 151 (passing) |
| Test files | 8 |
| Database tables | 10+ |
| API endpoints | 35+ |
| Dashboard pages | 9 feature pages (+ login, register) |
| Landing page | 1 (static) |
| Service modules | 7 (auth, contact, flow, campaign, template, analytics, billing) |
| Status | Feature-complete for MVP |

### Feature Completion

| Feature | Status | Notes |
|---------|--------|-------|
| User auth (register/login/refresh) | Complete | JWT + API key dual auth |
| Contact management (CRUD) | Complete | With tags, custom fields, subscription tracking |
| Bulk contact import (email + CSV) | Complete | Deduplication, plan limit enforcement |
| Contact lists (static + dynamic) | Complete | Rules-based dynamic lists |
| Email templates (system + custom) | Complete | Category filtering, HTML + text content |
| Automation flows (CRUD + lifecycle) | Complete | Draft/active/paused lifecycle, 5 trigger types |
| Flow executions tracking | Complete | Per-contact step-by-step progress |
| Broadcast campaigns (CRUD + send) | Complete | Mock send with event creation |
| Campaign analytics | Complete | Per-campaign and aggregate metrics |
| Email event tracking | Complete | Sent, delivered, opened, clicked, bounced, unsubscribed |
| Billing (plans, checkout, portal) | Complete | Stripe integration (mock mode in dev) |
| API keys (create, list, revoke) | Complete | SHA-256 hashed, scoped permissions |
| Usage reporting | Complete | Cross-service integration endpoint |
| CAN-SPAM compliance | Complete | Unsubscribe records, opt-out tracking |
| Dashboard UI | Complete | 9 pages with animations, KPI cards, dialogs |
| Landing page | Complete | Static marketing page |

---

## Metrics

| Category | Count |
|----------|-------|
| Backend tests | 151 |
| Dashboard feature pages | 9 (home, contacts, flows, campaigns, templates, analytics, API keys, billing, settings) |
| Auth pages | 2 (login, register) |
| API route modules | 13 (auth, contacts, flows, campaigns, templates, analytics, billing, api_keys, deps, health, usage, webhooks, __init__) |
| Service modules | 7 (auth, contact, flow, campaign, template, analytics, billing) |
| Database models | 10 (User, Subscription, ApiKey, Contact, ContactList, EmailTemplate, Flow, FlowExecution, Campaign, EmailEvent) |

---

## Pricing

FlowSend uses a three-tier pricing model, enforced at the API layer:

| Tier | Price/mo | Emails/mo | Contacts | Flows | A/B Testing | API Access | Trial |
|------|----------|----------|----------|-------|-------------|------------|-------|
| **Free** | $0 | 500 | 250 | 2 | No | No | -- |
| **Pro** | $39 | 25,000 | 10,000 | 20 | Yes | Yes | 14 days |
| **Enterprise** | $149 | Unlimited | Unlimited | Unlimited | Yes | Yes + Dedicated IP | 14 days |

### Plan Limit Enforcement

Plan limits are defined in `backend/app/constants/plans.py` as a `PlanLimits` dataclass:

- **max_items**: Maximum emails per month (-1 = unlimited)
- **max_secondary**: Maximum contacts (-1 = unlimited)
- **api_access**: Whether API key creation is enabled
- **trial_days**: Free trial period for paid plans

Limits are enforced at the API layer via dependency injection. When a user attempts to exceed their plan limits (e.g., creating more contacts than allowed), the API returns a 400 error with a descriptive message.

---

## Integration with Dropshipping Platform

FlowSend integrates with the dropshipping platform through:

1. **Provisioning API** (`POST /api/v1/auth/provision`): The platform can create FlowSend user accounts and receive API keys for managing them programmatically.
2. **Usage API** (`GET /api/v1/usage`): The platform can poll usage metrics for billing dashboard display.
3. **API Key Authentication**: Platform-generated API keys allow server-to-server communication via the `X-API-Key` header.
4. **External IDs**: Users provisioned from the platform have `external_platform_id` and `external_store_id` fields linking them to their platform account.

---

## Risk Register

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Email delivery (not yet real)** | Medium | Campaign sending is currently mocked. Production deployment requires integrating a real email provider (SendGrid, SES, etc.) via Celery tasks. |
| **A/B testing (Pro+)** | Low | Pricing mentions A/B testing for Pro+, but the feature is not yet fully implemented in the campaign model. Subject line variations need to be added. |
| **Flow execution at scale** | Medium | Celery task processing for flows is architecturally defined but needs load testing with large contact lists and complex multi-step flows. |
| **Stripe production mode** | Low | All billing tests run in mock mode. Production Stripe integration requires setting `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, and Price IDs via environment variables. |
| **Rate limiting** | Medium | No API rate limiting is currently implemented. High-volume API consumers could overwhelm the service. |
| **Template rendering** | Low | Templates store raw HTML. A preview/rendering engine for template design is not yet built. |
| **Contact import at scale** | Low | CSV import is synchronous. Very large imports (100K+ contacts) should be moved to a Celery background task. |

---

## Key Stakeholder Information

### Billing Configuration

The billing page in the dashboard displays plan cards driven by `dashboard/src/service.config.ts`. The backend enforces limits from `backend/app/constants/plans.py`. Both must be kept in sync when changing pricing.

### Dashboard Branding

The entire dashboard brand (name, tagline, colors, fonts, navigation) is controlled by a single file: `dashboard/src/service.config.ts`. Changing values there updates the entire UI without code changes.

- **Service name**: FlowSend
- **Tagline**: Smart Email Marketing
- **Primary color**: Coral Red (`#f43f5e`)
- **Accent color**: Orange (`#fb923c`)
- **Heading font**: Satoshi
- **Body font**: Source Sans 3

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
