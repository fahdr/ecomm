# PostPilot Setup Guide

> Part of [PostPilot](README.md) documentation

This guide covers local development setup, prerequisites, environment configuration, and running the PostPilot service stack.

---

## Prerequisites

### Required Software

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend API runtime |
| Node.js | 20+ | Dashboard and landing page runtime |
| PostgreSQL | 16+ | Database |
| Redis | 7+ | Cache and Celery broker |
| Docker + Docker Compose | Latest | Container orchestration (optional) |
| Make | Any | Build automation |

### Development Tools

- **pytest** + **pytest-asyncio** -- Backend testing
- **httpx** -- Async HTTP client for tests
- **Next.js** 16 -- Dashboard and landing page framework
- **Tailwind CSS** -- Styling framework

---

## Quick Start

### Using Make (Recommended)

```bash
# Navigate to PostPilot directory
cd /workspaces/ecomm/postpilot/

# Install all dependencies (Python + Node)
make install

# Run database migrations
make migrate

# Start all services (backend + dashboard + landing)
make start
```

### Manual Start

```bash
# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8106 --reload

# Dashboard (new terminal)
cd dashboard
npm install
npm run dev

# Landing (new terminal)
cd landing
npm install
npm run dev
```

---

## Service Ports

| Service | Port | Description | URL |
|---------|------|-------------|-----|
| Backend API | 8106 | FastAPI server with auto-reload | http://localhost:8106 |
| API Docs (Swagger) | 8106 | OpenAPI documentation | http://localhost:8106/docs |
| API Docs (ReDoc) | 8106 | Alternative API docs | http://localhost:8106/redoc |
| Dashboard | 3106 | Next.js dev server | http://localhost:3106 |
| Landing Page | 3206 | Next.js static landing | http://localhost:3206 |
| PostgreSQL | 5506 | Database server | localhost:5506 |
| Redis | 6406 | Cache and broker | localhost:6406 |

---

## Environment Variables

### Configuration File

Create a `.env` file in `/workspaces/ecomm/postpilot/` using `.env.example` as a template.

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...@db:5506/postpilot` | Async database connection string |
| `DATABASE_URL_SYNC` | `postgresql://...@db:5506/postpilot` | Sync URL for Alembic migrations |
| `REDIS_URL` | `redis://redis:6406/0` | Redis connection for caching |
| `CELERY_BROKER_URL` | `redis://redis:6406/1` | Celery broker (task queue) |
| `CELERY_RESULT_BACKEND` | `redis://redis:6406/2` | Celery results storage |
| `JWT_SECRET_KEY` | **(required)** | Secret for signing JWT tokens |

### Stripe Integration (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `STRIPE_SECRET_KEY` | `""` (mock mode) | Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | `""` (skip verification) | Stripe webhook signing secret |
| `STRIPE_PRO_PRICE_ID` | `""` | Stripe Price ID for Pro tier |
| `STRIPE_ENTERPRISE_PRICE_ID` | `""` | Stripe Price ID for Enterprise tier |

**Mock Mode:** When `STRIPE_SECRET_KEY` is empty, the billing service creates subscriptions directly in the database without calling Stripe. This enables full testing without Stripe credentials.

### Frontend Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8106` | Backend URL for dashboard/landing |

---

## Database Setup

### Running Migrations

```bash
# Automatic upgrade to latest version
make migrate

# Manual migration
cd backend
alembic upgrade head

# Create a new migration (after model changes)
cd backend
alembic revision --autogenerate -m "Description of changes"
alembic upgrade head
```

### Database Connection Details

| Parameter | Value |
|-----------|-------|
| Host | `localhost` (or `db` in Docker) |
| Port | `5506` |
| Database | `postpilot` |
| Username | `dropship` (or configured value) |
| Password | `dropship_dev` (or configured value) |

### Manual Database Access

```bash
# Connect via psql
psql postgresql://dropship:dropship_dev@localhost:5506/postpilot

# List tables
\dt

# Describe table
\d users
```

---

## Redis Setup

Redis is used for:
- **DB 0:** General caching
- **DB 1:** Celery broker (task queue)
- **DB 2:** Celery result backend

### Redis Connection

```bash
# Connect via redis-cli
redis-cli -h localhost -p 6406

# Select database
SELECT 0

# List all keys
KEYS *

# Flush specific database
FLUSHDB
```

---

## Running Tests

```bash
# All backend tests (157 tests)
make test-backend

# Verbose output with test names
cd backend && pytest -v

# Run specific test file
cd backend && pytest tests/test_posts.py -v

# Run single test
cd backend && pytest tests/test_queue.py::test_generate_caption_for_queue_item -v

# Run tests matching keyword
cd backend && pytest -k "calendar" -v

# Show test durations
cd backend && pytest --durations=10
```

See [Testing Guide](TESTING.md) for comprehensive test documentation.

---

## Development Workflow

### Making Backend Changes

1. Modify models in `backend/app/models/`
2. Generate migration: `cd backend && alembic revision --autogenerate -m "description"`
3. Review migration in `backend/alembic/versions/`
4. Apply migration: `alembic upgrade head`
5. Update services in `backend/app/services/`
6. Update API routes in `backend/app/api/`
7. Write tests in `backend/tests/`
8. Run tests: `pytest -v`

### Making Frontend Changes

1. Update pages in `dashboard/src/app/`
2. Update components in `dashboard/src/components/`
3. Update service config in `dashboard/src/service.config.ts` (branding, navigation, plans)
4. Test locally: `npm run dev`
5. Build for production: `npm run build`

### Celery Worker (Background Tasks)

```bash
# Start Celery worker (from backend directory)
cd backend
celery -A app.tasks.celery_app worker --loglevel=info

# Monitor tasks
celery -A app.tasks.celery_app events

# Purge all tasks
celery -A app.tasks.celery_app purge
```

---

## Troubleshooting

### Backend Won't Start

**Symptom:** FastAPI fails to start with database connection error

**Solutions:**
- Verify PostgreSQL is running: `pg_isready -h localhost -p 5506`
- Check `DATABASE_URL` in `.env`
- Run migrations: `make migrate`
- Check logs for specific error

### Dashboard Shows 401 Errors

**Symptom:** All API calls return 401 Unauthorized

**Solutions:**
- Verify backend is running on port 8106
- Check `NEXT_PUBLIC_API_URL` in `.env`
- Clear browser local storage (auth tokens may be expired)
- Check browser console for specific error messages

### Migrations Fail

**Symptom:** Alembic migration fails with "relation already exists"

**Solutions:**
- Check if migration was partially applied: `alembic current`
- Downgrade one version: `alembic downgrade -1`
- Review migration file for conflicts
- If corrupted, reset to base: `alembic downgrade base` then `alembic upgrade head`

### Redis Connection Refused

**Symptom:** Backend fails to connect to Redis

**Solutions:**
- Verify Redis is running: `redis-cli -h localhost -p 6406 ping`
- Check `REDIS_URL` in `.env`
- Restart Redis: `docker restart postpilot_redis` (if using Docker)

---

## Docker Compose

If running via Docker Compose:

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Stop all services
docker compose down

# Rebuild after changes
docker compose up -d --build

# Access backend shell
docker compose exec backend bash

# Access database shell
docker compose exec db psql -U dropship -d postpilot
```

---

*See also: [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md) · [README](README.md)*
