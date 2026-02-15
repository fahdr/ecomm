# Setup Guide

> Part of [Dropshipping Platform](README.md) documentation

## Prerequisites

- VS Code with the Dev Containers extension
- Docker Desktop running

## Starting the Environment

1. Open the project root in VS Code
2. Command Palette → **Dev Containers: Reopen in Container**
3. The container installs Python and Node dependencies automatically via `postCreateCommand`

## Services

All services run in the devcontainer. Open a separate terminal for each:

```bash
# Backend API — http://localhost:8000
cd /workspaces/ecomm/dropshipping/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Dashboard — http://localhost:3000
cd /workspaces/ecomm/dropshipping/dashboard
npm run dev

# Storefront — http://localhost:3001
cd /workspaces/ecomm/dropshipping/storefront
npm run dev -- -p 3001

# Celery worker
cd /workspaces/ecomm/dropshipping/backend
celery -A app.tasks.celery_app worker --loglevel=info

# Celery Beat (scheduler)
cd /workspaces/ecomm/dropshipping/backend
celery -A app.tasks.celery_app beat --loglevel=info

# Flower (task monitor, optional) — http://localhost:5555
cd /workspaces/ecomm/dropshipping/backend
celery -A app.tasks.celery_app flower --port=5555
```

## Seed Data

Populate the database with a complete demo dataset for the Volt Electronics store:

```bash
cd /workspaces/ecomm
npx tsx scripts/seed.ts
```

The seed script is **idempotent** — it checks for existing records before creating new ones. **Prerequisites:** The backend must be running on port 8000 with migrations applied (`alembic upgrade head`).

| Data | Count | Details |
|------|-------|---------|
| User account | 1 | `demo@example.com` / `password123` |
| Store | 1 | "Volt Electronics" (slug: `volt-electronics`) |
| Categories | 6 | 4 top-level + 2 sub-categories |
| Products | 12 | Rich descriptions, Unsplash images, 2-4 variants each |
| Suppliers | 3 | Linked to all 12 products with cost data |
| Discount codes | 5 | WELCOME10, SUMMER25, FLAT20, AUDIO15, BIGSPEND50 |
| Tax rates | 4 | CA, NY, TX sales tax + UK VAT |
| Gift cards | 3 | $25, $50, $100 |
| Customer accounts | 3 | alice/bob/carol@example.com (all `password123`) |
| Orders | 4 | Full lifecycle: pending → paid → shipped → delivered |
| Reviews | 14 | Across 8 products, 3-5 star ratings |
| Theme | 1 | Cyberpunk preset with 8 custom blocks |

**Demo-specific features to verify after seeding:**
- **Sale badges** — 4 products have `compare_at_price` set
- **Inventory alerts** — NovaBand and MagFloat have low stock (2-4 units)
- **Theme blocks** — Cyberpunk theme with hero, countdown, carousel, testimonials, trust badges, newsletter

## Demo Credentials

| Role | Email | Password | Access |
|------|-------|----------|--------|
| **Store Owner** | `demo@example.com` | `password123` | Dashboard: `http://localhost:3000` |
| **Customer (Alice)** | `alice@example.com` | `password123` | Storefront: `http://localhost:3001?store=volt-electronics` |
| **Customer (Bob)** | `bob@example.com` | `password123` | Storefront: `http://localhost:3001?store=volt-electronics` |
| **Customer (Carol)** | `carol@example.com` | `password123` | Storefront: `http://localhost:3001?store=volt-electronics` |

## Ports

| Port | Service |
|------|---------|
| 8000 | Backend API |
| 3000 | Dashboard |
| 3001 | Storefront |
| 5432 | PostgreSQL |
| 6379 | Redis |
| 5555 | Flower |

## Environment Variables

Pre-configured in `.devcontainer/docker-compose.yml`:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | `postgresql+asyncpg://dropship:dropship_dev@db:5432/dropshipping` |
| `DATABASE_URL_SYNC` | `postgresql://dropship:dropship_dev@db:5432/dropshipping` |
| `REDIS_URL` | `redis://redis:6379/0` |
| `CELERY_BROKER_URL` | `redis://redis:6379/1` |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/2` |

## Database Migrations

```bash
cd /workspaces/ecomm/dropshipping/backend

# Create a new migration after model changes
alembic revision --autogenerate -m "description of changes"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# See current migration state
alembic current

# Merge multiple heads
alembic merge heads -m "merge heads"
```

Alembic is configured for async via `asyncpg`. There are currently 13 migrations managing ~37 database tables.

---
*See also: [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
