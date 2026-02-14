# Setup Guide

> Part of [SpyDrop](README.md) documentation

This guide covers how to set up SpyDrop for local development, including prerequisites, environment variables, ports, and service startup commands.

---

## Prerequisites

| Requirement | Version | Purpose |
|------------|---------|---------|
| Python | 3.12+ | Backend API |
| Node.js | 20+ | Dashboard and landing page |
| PostgreSQL | 16 | Database |
| Redis | 7 | Cache, Celery broker/backend |
| Docker + Docker Compose | Latest | Recommended for local dev |

---

## Quick Start

### With Docker Compose (Recommended)

```bash
# From /workspaces/ecomm/spydrop/
make install     # Install Python + Node dependencies
make migrate     # Run Alembic migrations
make start       # Start all services (backend, dashboard, landing)
```

### Manual Start (without Docker)

```bash
# 1. Start PostgreSQL (port 5505) and Redis (port 6405)
# Ensure DATABASE_URL and REDIS_URL point to running instances

# 2. Install backend dependencies
cd backend
pip install -r requirements.txt

# 3. Run migrations
cd backend
alembic upgrade head

# 4. Start backend API
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8105

# 5. Install dashboard dependencies (separate terminal)
cd dashboard
npm install

# 6. Start dashboard
cd dashboard
npm run dev

# 7. Start landing page (separate terminal)
cd landing
npm install
npm run dev
```

---

## Access Points

| Service | URL | Description |
|---------|-----|-------------|
| Backend API | http://localhost:8105 | FastAPI application (main service) |
| API Docs (Swagger) | http://localhost:8105/docs | Interactive API documentation |
| Dashboard | http://localhost:3105 | Next.js dashboard (App Router) |
| Landing Page | http://localhost:3205 | Static marketing site |

---

## Ports

| Port | Service | Protocol | Notes |
|------|---------|----------|-------|
| 8105 | Backend API (FastAPI) | HTTP | Main service port |
| 3105 | Dashboard (Next.js) | HTTP | Development server |
| 3205 | Landing Page (Next.js) | HTTP | Static export during dev |
| 5505 | PostgreSQL 16 | TCP | Database port |
| 6405 | Redis 7 | TCP | Cache and Celery |

All ports are unique to SpyDrop to avoid conflicts with other services in the monorepo.

---

## Environment Variables

### Backend Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://dropship:dropship_dev@db:5505/spydrop` | Async PostgreSQL connection |
| `DATABASE_URL_SYNC` | `postgresql://dropship:dropship_dev@db:5505/spydrop` | Sync connection (Alembic) |
| `REDIS_URL` | `redis://redis:6405/0` | Redis cache |
| `CELERY_BROKER_URL` | `redis://redis:6405/1` | Celery task broker |
| `CELERY_RESULT_BACKEND` | `redis://redis:6405/2` | Celery result storage |
| `JWT_SECRET_KEY` | (required) | Secret for signing JWT tokens |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token TTL |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |
| `STRIPE_SECRET_KEY` | (empty = mock mode) | Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | (empty = mock mode) | Stripe webhook signature secret |
| `STRIPE_BILLING_SUCCESS_URL` | `http://localhost:3105/billing` | Checkout success redirect |
| `STRIPE_BILLING_CANCEL_URL` | `http://localhost:3105/billing` | Checkout cancel redirect |

### Dashboard Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8105` | Backend API URL (client-side) |

### Development Notes

- **Mock Mode:** When `STRIPE_SECRET_KEY` is empty, all billing operations bypass Stripe API calls and create subscriptions directly in the database. This enables full development without a Stripe account.
- **JWT Secret:** Generate a secure secret: `openssl rand -hex 32`

---

## Database Migrations

SpyDrop uses Alembic for database schema migrations.

### Create a New Migration

```bash
cd backend
alembic revision --autogenerate -m "description of change"
```

This generates a new migration file in `backend/alembic/versions/`.

### Apply All Migrations

```bash
# Using Makefile
make migrate

# Or directly
cd backend
alembic upgrade head
```

### Check Current Migration State

```bash
cd backend
alembic current
```

### Merge Multiple Heads (Parallel Development)

If multiple developers create migrations simultaneously, Alembic may create branches.

```bash
cd backend
alembic merge heads -m "merge heads"
```

---

## Services Start Commands

| Service | Command | Working Directory |
|---------|---------|------------------|
| Backend API | `uvicorn app.main:app --reload --host 0.0.0.0 --port 8105` | `backend/` |
| Dashboard | `npm run dev` | `dashboard/` |
| Landing Page | `npm run dev` | `landing/` |
| Celery Worker | `celery -A app.tasks.celery_app worker --loglevel=info` | `backend/` |
| Celery Beat | `celery -A app.tasks.celery_app beat --loglevel=info` | `backend/` |

### Using Make Targets

```bash
make test-backend      # Run pytest
make start             # Start all services via docker-compose
make stop              # Stop all services
make logs              # Tail logs
make shell             # Open backend shell
```

---

## Testing the Setup

After starting all services, verify:

1. **Backend health check:** `curl http://localhost:8105/api/v1/health`
   - Should return: `{"service": "spydrop", "status": "ok", "timestamp": "..."}`

2. **API docs accessible:** Open http://localhost:8105/docs in browser
   - Should display interactive Swagger UI

3. **Dashboard loads:** Open http://localhost:3105
   - Should display SpyDrop dashboard home page

4. **Landing page loads:** Open http://localhost:3205
   - Should display marketing site

5. **Database connected:** Check backend logs for "Database connected" message

6. **Redis connected:** Check backend logs for successful Redis connection

---

## Troubleshooting

### Port Already in Use

If a port is already allocated, check for conflicting services:

```bash
# Find process using port 8105
lsof -i :8105

# Kill process (if safe)
kill -9 <PID>
```

### Database Connection Failed

- Verify PostgreSQL is running: `pg_isready -h localhost -p 5505`
- Check `DATABASE_URL` matches PostgreSQL credentials
- Run migrations: `make migrate`

### Redis Connection Failed

- Verify Redis is running: `redis-cli -p 6405 ping`
- Check `REDIS_URL` points to correct host/port

### Alembic Migration Errors

- Ensure database is accessible
- Check for migration conflicts: `alembic heads`
- Merge heads if multiple branches exist: `alembic merge heads -m "merge"`

### Node Module Errors

```bash
# Clear node_modules and reinstall
cd dashboard
rm -rf node_modules package-lock.json
npm install

cd ../landing
rm -rf node_modules package-lock.json
npm install
```

---

*See also: [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md) · [README](README.md)*
