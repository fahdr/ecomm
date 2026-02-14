# RankPilot Documentation

> Part of [RankPilot](README.md) documentation

## Overview

RankPilot is an **Automated SEO Engine** -- a standalone SaaS product that automates search engine optimization for e-commerce stores. It manages sitemaps, JSON-LD schema markup, AI-generated blog posts, keyword rank tracking, and comprehensive SEO audits. RankPilot can be used independently or integrated with the dropshipping platform via cross-service provisioning and API key authentication.

**Feature designation:** A3 in the platform roadmap
**Position:** Most feature-rich service in the ecosystem (20+ API endpoints)

## Quick Start

```bash
# Install dependencies, run migrations, and start all services
make install && make migrate && make start
```

Access points:
- **API**: http://localhost:8103
- **API Docs**: http://localhost:8103/docs
- **Dashboard**: http://localhost:3103
- **Landing Page**: http://localhost:3203

## Documentation

| Document | Audience | Purpose |
|----------|----------|---------|
| [Setup](SETUP.md) | Developers | Local development environment, prerequisites, ports, services |
| [Architecture](ARCHITECTURE.md) | Developers | Tech stack, project structure, design decisions, database schema |
| [API Reference](API_REFERENCE.md) | Developers, QA | Endpoint documentation, request/response formats, conventions |
| [Testing](TESTING.md) | Developers, QA | Test infrastructure, running tests, writing tests, fixtures |
| [QA Engineer Guide](QA_ENGINEER.md) | QA Engineers | Acceptance criteria, verification checklists, edge cases |
| [Project Manager Guide](PROJECT_MANAGER.md) | Project Managers | Feature scope, progress metrics, pricing model, integration |
| [End User Guide](END_USER.md) | End Users | Feature guides, workflows, subscription tiers, getting started |
| [Implementation Steps](IMPLEMENTATION_STEPS.md) | All | Build history, step-by-step implementation record |

## Key Metrics

| Metric | Value |
|--------|-------|
| Backend Tests | **165** |
| Test Files | 8 |
| API Route Files | 13 (5 domain-specific + 8 standard) |
| Service Modules | 7 |
| Database Models | 9 |
| Dashboard Pages | 9 |
| API Endpoints | 20+ |

## Features

### Core SEO Features

1. **Site Management** -- Register domains, verify ownership, manage sitemaps
2. **AI Blog Posts** -- Generate SEO-optimized content with target keywords
3. **Keyword Tracking** -- Monitor search rankings, volume, difficulty
4. **SEO Audits** -- Automated health checks with scoring (0-100)
5. **Schema Markup** -- JSON-LD structured data for rich snippets

### Platform Integration

- **User Provisioning**: `/auth/provision` endpoint for cross-service account creation
- **Usage Reporting**: `/usage` endpoint for aggregated billing dashboards
- **API Key Authentication**: Pro/Enterprise users get programmatic access

## Pricing Tiers

| Tier | Monthly | Blog Posts | Keywords | Sites | API |
|------|---------|------------|----------|-------|-----|
| Free | $0 | 2/month | 20 | 1 | No |
| Pro | $29 | 20/month | 200 | 5 | Yes |
| Enterprise | $99 | Unlimited | Unlimited | Unlimited | Yes |

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
