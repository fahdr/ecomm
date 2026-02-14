# AdScale Documentation

> Part of [AdScale](README.md) documentation

**AdScale** is an AI-powered ad campaign management service that enables dropshipping store owners to manage advertising across Google Ads and Meta (Facebook + Instagram) from a unified dashboard. It features AI-generated ad copy, automated optimization rules, and ROAS-focused performance analytics.

---

## Overview

AdScale (Feature A7) provides dual-platform advertising management with AI-driven automation. Store owners can launch campaigns, generate compelling ad copy with Claude AI, set up automated rules to pause underperformers or scale winners, and track performance with centralized ROAS analytics.

### Quick Stats

| Metric | Value |
|--------|-------|
| **Backend Tests** | 164 passing |
| **API Endpoints** | 35+ across 9 route modules |
| **Database Tables** | 10 (users, subscriptions, api_keys, ad_accounts, campaigns, ad_groups, ad_creatives, campaign_metrics, optimization_rules, alembic_version) |
| **Dashboard Pages** | 9 (home, campaigns, creatives, analytics, billing, api-keys, settings, login, register) |
| **Service Layer Files** | 7 (auth, account, campaign, creative, metrics, optimization, billing) |

---

## Key Features

- **Dual-Platform Support** -- Manage Google Ads and Meta Ads from one unified interface
- **AI Ad Copy Generation** -- Claude-powered headline, description, and CTA generation from product descriptions
- **Auto-Optimization Rules** -- Set-and-forget rules that pause low-ROAS campaigns, scale high-performers, or adjust budgets automatically
- **ROAS-First Analytics** -- Performance dashboard built around Return on Ad Spend
- **Cascading Resource Model** -- User → Ad Account → Campaign → Ad Group → Creative
- **Plan-Based Limits** -- Free (2 campaigns), Pro (25 campaigns), Enterprise (unlimited)

---

## Documentation Structure

| Document | Description |
|----------|-------------|
| **[Setup Guide](SETUP.md)** | Prerequisites, local development, ports, environment variables, starting services |
| **[Architecture](ARCHITECTURE.md)** | Tech stack, project structure, database schema, design decisions, ownership model |
| **[API Reference](API_REFERENCE.md)** | API endpoints, authentication, request/response patterns, error codes |
| **[Testing Guide](TESTING.md)** | Test stack, running tests, coverage table, writing tests, fixtures |
| **[QA Engineer Guide](QA_ENGINEER.md)** | Acceptance criteria, verification checklists, edge cases |
| **[Project Manager Guide](PROJECT_MANAGER.md)** | Feature status, pricing model, integration points, risk register |
| **[End User Guide](END_USER.md)** | User workflows, feature tutorials, subscription tiers, getting started |
| **[Implementation Steps](IMPLEMENTATION_STEPS.md)** | Step-by-step implementation history from scaffolding to completion |

---

## Quick Start

```bash
# From the service root
make install && make migrate && make start
```

Access the services:
- Backend API: http://localhost:8107
- API Docs: http://localhost:8107/docs
- Dashboard: http://localhost:3107
- Landing Page: http://localhost:3207

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
