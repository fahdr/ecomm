# Dropshipping Platform

> Multi-tenant SaaS for creating and managing automated dropshipping stores. Consists of a **Backend** (FastAPI, 36 routers, 22 models), **Dashboard** (Next.js, 34 pages), and **Storefront** (Next.js, 18 pages, 13 block types, 11 preset themes). Integrates with 8 SaaS services via the **ServiceBridge** event system.

## Quick Start

```bash
# Backend API — http://localhost:8000
cd /workspaces/ecomm/dropshipping/backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Dashboard — http://localhost:3000
cd /workspaces/ecomm/dropshipping/dashboard && npm run dev

# Storefront — http://localhost:3001
cd /workspaces/ecomm/dropshipping/storefront && npm run dev -- -p 3001

# Seed demo data
cd /workspaces/ecomm && npx tsx scripts/seed.ts
```

**Demo login:** `demo@example.com` / `password123` at `http://localhost:3000`

## Documentation

| Document | Audience | Description |
|----------|----------|-------------|
| [Setup Guide](SETUP.md) | Developers | Prerequisites, services, seed data, ports, env vars |
| [Architecture](ARCHITECTURE.md) | Developers | Tech stack, project structure, ServiceBridge, themes, design decisions |
| [API Reference](API_REFERENCE.md) | Developers / QA | Endpoints, conventions, schemas, Swagger links |
| [Testing](TESTING.md) | Developers / QA | Test stack, commands, coverage, fixtures, writing tests |
| [QA Engineer Guide](QA_ENGINEER.md) | QA Engineers | Acceptance criteria, verification checklists, edge cases |
| [Project Manager Guide](PROJECT_MANAGER.md) | Project Managers | Milestones, roadmap, metrics, risks |
| [End User Guide](END_USER.md) | End Users | Feature guide, workflows, getting started |
| [Implementation Steps](IMPLEMENTATION_STEPS.md) | All | Step-by-step build history |

## Key Metrics

| Metric | Count |
|--------|-------|
| Backend tests | 580 |
| E2E tests | 200+ |
| API routers | 36 |
| Database models | 22 |
| Dashboard pages | 34 |
| Storefront pages | 18 |
| Preset themes | 11 |
| Block types | 13 |
| Celery tasks | 21 |
| ServiceBridge events | 5 |
