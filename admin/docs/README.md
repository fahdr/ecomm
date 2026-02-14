# Super Admin Dashboard

> Centralized platform management service for the ecomm monorepo

## Overview

The Super Admin Dashboard is the control plane for monitoring and managing the entire ecomm platform. It provides:

- **Service Health Monitoring:** Real-time health checks for 8 SaaS services + LLM Gateway
- **LLM Gateway Management:** Configure AI providers, view usage analytics, track costs
- **Platform Oversight:** Admin authentication, service status history, cost breakdowns

**Key Metrics:**
- 34 backend tests (4 test modules)
- Backend port: 8300
- Dashboard port: 3300
- 2 database tables: `admin_users`, `admin_health_snapshots`

## Architecture

The admin service consists of:
- FastAPI backend (Python 3.11+) on port 8300
- Next.js dashboard (TypeScript/React) on port 3300
- Dedicated admin authentication (separate from platform users)
- LLM Gateway proxy (all provider/usage management)

## Quick Start

```bash
# From admin/backend:
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8300

# From admin/dashboard:
npm install
npm run dev  # Runs on port 3300
```

## Documentation

| Document                                | Purpose                                       |
|-----------------------------------------|-----------------------------------------------|
| [SETUP.md](SETUP.md)                    | Installation, ports, environment setup        |
| [ARCHITECTURE.md](ARCHITECTURE.md)      | Tech stack, design decisions, structure       |
| [API_REFERENCE.md](API_REFERENCE.md)    | Endpoint reference, request/response schemas  |
| [TESTING.md](TESTING.md)                | Test stack, running tests, coverage           |
| [QA_ENGINEER.md](QA_ENGINEER.md)        | Acceptance criteria, verification checklists  |
| [PROJECT_MANAGER.md](PROJECT_MANAGER.md)| Scope, dependencies, delivery milestones      |
| [END_USER.md](END_USER.md)              | Admin workflows, UI walkthroughs              |

## Managed Services

The admin dashboard monitors:
- **llm-gateway** (8200) — AI inference proxy
- **trendscout** (8101) — Product trend discovery
- **contentforge** (8102) — AI content generation
- **priceoptimizer** (8103) — Dynamic pricing engine
- **reviewsentinel** (8104) — Review fraud detection
- **inventoryiq** (8105) — Inventory forecasting
- **customerinsight** (8106) — Customer analytics
- **adcreator** (8107) — Ad creative generator
- **competitorradar** (8108) — Competitor tracking

---
*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
