# ContentForge Documentation

> AI-powered content generation SaaS for e-commerce product listings

**ContentForge** is an independently hostable SaaS product that generates SEO-optimized product titles, descriptions, meta tags, keywords, and bullet points using Claude AI. It also handles product image download, optimization, and format conversion via Pillow.

---

## Quick Start

```bash
make install && make migrate && make start
```

Access points:
- **Backend API**: http://localhost:8102
- **API Docs**: http://localhost:8102/docs
- **Dashboard**: http://localhost:3102
- **Landing Page**: http://localhost:3202

---

## Documentation Index

| Document | Audience | Purpose |
|----------|----------|---------|
| [Setup](SETUP.md) | Developers | Local environment setup, dependencies, services |
| [Architecture](ARCHITECTURE.md) | Developers | Tech stack, design decisions, project structure |
| [API Reference](API_REFERENCE.md) | Developers/QA | Endpoint documentation, request/response formats |
| [Testing](TESTING.md) | Developers/QA | Test infrastructure, running tests, writing tests |
| [QA Engineer](QA_ENGINEER.md) | QA Engineers | Acceptance criteria, verification checklists |
| [Project Manager](PROJECT_MANAGER.md) | Project Managers | Scope, status, pricing, roadmap alignment |
| [End User](END_USER.md) | End Users | Feature guides, workflows, getting started |
| [Implementation Steps](IMPLEMENTATION_STEPS.md) | All | Step-by-step build history |

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Backend tests | 116 |
| API endpoints | 26 |
| Database tables | 7 |
| Dashboard pages | 8 |
| Subscription tiers | 3 (Free, Pro, Enterprise) |
| System templates | 4 (Professional, Casual, Luxury, SEO-Focused) |

---

## Service Ports

| Service | Port | Purpose |
|---------|------|---------|
| Backend API | 8102 | FastAPI REST API |
| Dashboard | 3102 | Next.js admin dashboard |
| Landing Page | 3202 | Next.js marketing site |
| PostgreSQL | 5502 | Database |
| Redis | 6402 | Cache and Celery broker |

---

## Features

- **AI Content Generation**: Claude-powered product copy in multiple tones
- **Image Optimization**: Pillow-based download, resize, WebP conversion
- **Template System**: System + custom templates for brand consistency
- **Bulk Generation**: CSV/URL batch processing (Pro/Enterprise)
- **Pricing Calculator**: Markup with psychological rounding ($X.99, $X.95)
- **API Access**: REST API with JWT and API key authentication

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
