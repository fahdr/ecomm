# TrendScout Documentation

> Part of the TrendScout service suite

**TrendScout** is an AI-powered product research SaaS that discovers trending, high-potential products using multi-source data aggregation and weighted scoring. It scans AliExpress, TikTok, Google Trends, and Reddit to identify winning dropshipping opportunities before your competitors.

---

## Quick Start

```bash
# Install dependencies and start services
make install
make migrate
make start
```

The service will be available at:
- Backend API: http://localhost:8101 (Swagger at `/docs`)
- Dashboard: http://localhost:3101
- Landing Page: http://localhost:3201

---

## Documentation Overview

| Document | Audience | Purpose |
|----------|----------|---------|
| [Setup Guide](SETUP.md) | Developers | Local development setup, prerequisites, services |
| [Architecture](ARCHITECTURE.md) | Developers | Tech stack, project structure, design decisions |
| [API Reference](API_REFERENCE.md) | Developers, QA | Complete API documentation, endpoints, schemas |
| [Testing Guide](TESTING.md) | Developers, QA | Test stack, running tests, coverage, fixtures |
| [QA Engineer Guide](QA_ENGINEER.md) | QA Engineers | Acceptance criteria, verification checklists |
| [Project Manager Guide](PROJECT_MANAGER.md) | PMs, Stakeholders | Project overview, status, metrics, roadmap |
| [End User Guide](END_USER.md) | End Users | Feature usage, workflows, FAQ |
| [Implementation Steps](IMPLEMENTATION_STEPS.md) | Developers, PMs | Step-by-step build history |

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Backend Tests | 158 |
| Dashboard Pages | 8 |
| Landing Pages | 2 |
| API Endpoints | 22+ |
| Database Models | 7 |
| Service Port | 8101 |
| Dashboard Port | 3101 |
| Landing Port | 3201 |

---

## Feature Highlights

- **Multi-Source Research**: Aggregate data from AliExpress, TikTok, Google Trends, and Reddit
- **AI-Powered Scoring**: Weighted composite scores (0-100) across 5 dimensions
- **Deep AI Analysis**: Claude-powered insights on opportunity, risk, pricing, and marketing
- **Watchlist Management**: Save, annotate, and track products through the sales lifecycle
- **Standalone + Integrated**: Works independently or as a platform add-on via provision API
- **Plan-Gated Features**: Tiered access with enforced resource limits (Free/Pro/Enterprise)

---

## Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + SQLAlchemy 2.0 (async) + Celery |
| Frontend | Next.js 16 + Tailwind CSS |
| Database | PostgreSQL 16 |
| Cache/Queue | Redis 7 |
| AI | Anthropic Claude API |
| Billing | Stripe |
| Testing | pytest + httpx |

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
