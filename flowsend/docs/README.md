# FlowSend Documentation

> **Smart Email Marketing** — Automated email flows, broadcast campaigns, and delivery analytics

FlowSend is an independently hostable SaaS product providing complete email marketing automation with contact management, visual flow builders, broadcast campaigns, email templates, A/B testing (Pro+), and analytics.

## Quick Links

| Document | Description |
|----------|-------------|
| [Setup Guide](SETUP.md) | Local development environment, ports, services, environment variables |
| [Architecture](ARCHITECTURE.md) | Tech stack, project structure, database schema, design decisions |
| [API Reference](API_REFERENCE.md) | Complete endpoint documentation, request/response formats |
| [Testing Guide](TESTING.md) | Test infrastructure, running tests, coverage, writing new tests |
| [QA Engineer Guide](QA_ENGINEER.md) | Acceptance criteria, verification checklists, edge cases |
| [Project Manager Guide](PROJECT_MANAGER.md) | Feature scope, milestones, metrics, risk register |
| [End User Guide](END_USER.md) | User workflows, dashboard navigation, getting started |
| [Implementation Steps](IMPLEMENTATION_STEPS.md) | Complete build history from scaffolding to deployment |

## Key Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Backend Tests** | 151 | Highest test count across all services |
| **Database Tables** | 10+ | Most complex data model in the platform |
| **API Endpoints** | 35+ | Auth, contacts, flows, campaigns, templates, analytics, billing |
| **Dashboard Pages** | 9 feature pages | Plus login and registration |
| **Service Modules** | 7 | Dedicated logic for each domain |
| **Ports** | 8104 (API), 3104 (Dashboard), 3204 (Landing), 5504 (DB), 6404 (Redis) | |

## Architecture at a Glance

```
flowsend/
├── backend/            FastAPI + SQLAlchemy 2.0 (async)
│   ├── app/
│   │   ├── api/        13 route modules (auth, contacts, flows, campaigns, etc.)
│   │   ├── models/     10+ database models
│   │   ├── services/   7 business logic modules
│   │   ├── schemas/    Request/response validation
│   │   └── constants/  Plan limits, config
│   └── tests/          151 tests across 8 files
├── dashboard/          Next.js 16 dashboard (9 feature pages)
└── landing/            Next.js static landing page
```

## Core Features

- **Contact Management** — Import, tag, search, organize into static/dynamic lists
- **Automation Flows** — Trigger-based sequences (signup, purchase, abandoned cart, custom, scheduled)
- **Broadcast Campaigns** — One-time emails with scheduling and analytics
- **Email Templates** — System and custom templates with category organization
- **Analytics** — Delivery, open, click, bounce tracking with aggregate and per-campaign views
- **CAN-SPAM Compliance** — Built-in unsubscribe handling and subscription tracking
- **API Keys** — SHA-256 hashed keys for programmatic access
- **Billing** — Stripe integration with 3-tier pricing (Free, Pro $39, Enterprise $149)

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
