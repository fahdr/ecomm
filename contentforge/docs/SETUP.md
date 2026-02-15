# Setup Guide

> Part of [ContentForge](README.md) documentation

This guide covers prerequisites, local development setup, environment variables, and service management for ContentForge.

---

## Prerequisites

- **Python 3.12** or later
- **Node.js 18** or later with npm
- **PostgreSQL 16** (provided by devcontainer)
- **Redis 7** (provided by devcontainer)
- **Docker** (for devcontainer services)

---

## Local Dev Setup

ContentForge runs on three processes locally:
- FastAPI backend (port 8102)
- Next.js dashboard (port 3102)
- Next.js landing page (port 3202)

PostgreSQL and Redis are provided by the devcontainer.

### Quick Start

```bash
make install && make migrate && make start
```

This command sequence:
1. Installs backend (pip) and frontend (npm) dependencies
2. Runs database migrations via Alembic
3. Starts all three services in parallel

### Access Points

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8102 |
| API Docs (Swagger) | http://localhost:8102/docs |
| ReDoc | http://localhost:8102/redoc |
| Dashboard | http://localhost:3102 |
| Landing Page | http://localhost:3202 |

---

## Services

### Start All Services

```bash
make start
```

Runs backend, dashboard, and landing page in parallel.

### Start Individual Services

**Backend only:**
```bash
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8102 --reload
```

**Dashboard only:**
```bash
cd dashboard && npm run dev -- --port 3102
```

**Landing page only:**
```bash
cd landing && npm run dev -- --port 3202
```

**Celery worker (async task processing):**
```bash
cd backend && celery -A app.tasks worker -Q contentforge --loglevel=info
```

### Stop All Services

```bash
make stop
```

---

## Install Dependencies

### Backend

```bash
cd backend && pip install -r requirements.txt
```

**Core dependencies:**
- FastAPI + uvicorn (API framework)
- SQLAlchemy 2.0 + asyncpg (async ORM)
- Alembic (migrations)
- Celery + redis (task queue)
- Pillow (image processing)
- bcrypt + pyjwt (auth)
- httpx (HTTP client for tests)
- pytest + pytest-asyncio (testing)
- stripe (billing)
- anthropic (AI content generation)

### Dashboard

```bash
cd dashboard && npm install
```

**Core dependencies:**
- Next.js 16 (React framework with App Router)
- Tailwind CSS 4.x (styling)
- lucide-react (icons)
- TypeScript (type safety)

### Landing Page

```bash
cd landing && npm install
```

Same dependencies as dashboard.

---

## Environment Variables

ContentForge uses environment variables for configuration. The devcontainer provides defaults; override by creating a `.env` file in the `contentforge/` root.

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://dropship:dropship_dev@db:5502/contentforge` | Async database connection string |
| `DATABASE_URL_SYNC` | `postgresql://dropship:dropship_dev@db:5502/contentforge` | Sync database connection string (for Alembic) |

### Redis

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6402/0` | Redis connection for caching |
| `CELERY_BROKER_URL` | `redis://redis:6402/1` | Celery task broker |
| `CELERY_RESULT_BACKEND` | `redis://redis:6402/2` | Celery result backend |

### Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | (generated) | JWT signing key (auto-generated if not set) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | JWT access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | JWT refresh token lifetime |

### Stripe (Billing)

| Variable | Default | Description |
|----------|---------|-------------|
| `STRIPE_SECRET_KEY` | (empty) | Stripe API secret key (empty = mock mode) |
| `STRIPE_WEBHOOK_SECRET` | (empty) | Stripe webhook signing secret (empty = mock mode) |
| `STRIPE_PRO_PRICE_ID` | (empty) | Stripe Price ID for Pro tier |
| `STRIPE_ENTERPRISE_PRICE_ID` | (empty) | Stripe Price ID for Enterprise tier |

**Mock mode:** When `STRIPE_SECRET_KEY` is not set, billing operates in mock mode. Checkout creates subscriptions directly in the database without calling Stripe's API.

### Anthropic (AI)

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (empty) | Claude AI API key for content generation (empty = mock mode) |

**Mock mode:** When `ANTHROPIC_API_KEY` is not set, content generation produces realistic mock text via `generate_mock_content()`. This enables full local development without AI API costs.

---

## Database Migrations

ContentForge uses Alembic for schema migrations with the async SQLAlchemy engine.

### Create a New Migration

```bash
cd backend && alembic revision --autogenerate -m "description of change"
```

Alembic inspects your models and generates a migration script in `backend/alembic/versions/`.

### Run Pending Migrations

```bash
cd backend && alembic upgrade head
```

Or use the Makefile:

```bash
make migrate
```

### Rollback the Last Migration

```bash
cd backend && alembic downgrade -1
```

### View Migration History

```bash
cd backend && alembic history
```

### Merge Multiple Heads

If parallel development creates multiple migration branches:

```bash
cd backend && alembic merge heads -m "merge heads"
```

---

## Testing

### Run All Backend Tests

```bash
make test-backend
```

Runs 116 backend tests across 7 test files.

### Run Specific Test Files

```bash
cd backend && pytest tests/test_content.py -v
cd backend && pytest tests/test_templates.py -v
cd backend && pytest tests/test_images.py -v
cd backend && pytest tests/test_auth.py -v
cd backend && pytest tests/test_billing.py -v
cd backend && pytest tests/test_api_keys.py -v
cd backend && pytest tests/test_health.py -v
```

### Run a Single Test

```bash
cd backend && pytest tests/test_content.py::test_create_generation_job_from_url -v
```

See [Testing](TESTING.md) for detailed test architecture documentation.

---

## Troubleshooting

### Backend won't start

**Error:** `ModuleNotFoundError: No module named 'app'`

**Solution:** Install backend dependencies:
```bash
cd backend && pip install -r requirements.txt
```

### Database connection refused

**Error:** `could not connect to server: Connection refused`

**Solution:** Ensure PostgreSQL is running via the devcontainer. Check the devcontainer status and restart if needed.

### Migration conflicts

**Error:** `Multiple head revisions are present`

**Solution:** Merge migration heads:
```bash
cd backend && alembic merge heads -m "merge heads"
cd backend && alembic upgrade head
```

### Port already in use

**Error:** `OSError: [Errno 48] Address already in use`

**Solution:** Stop the conflicting service or change the port in the command.

---

*See also: [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md) · [README](README.md)*
