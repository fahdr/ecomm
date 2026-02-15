# AdScale Setup Guide

> Part of [AdScale](README.md) documentation

This guide covers local development setup, environment configuration, and service startup for the AdScale AI Ad Campaign Manager service.

---

## Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Docker + Docker Compose | Latest | Container orchestration |
| Node.js | 20+ | Dashboard and landing page |
| Python | 3.12+ | Backend API |
| PostgreSQL | 16 | Database |
| Redis | 7 | Cache and queue broker |
| Make | Latest | Build automation |

---

## Service Ports

| Service | Port | URL |
|---------|------|-----|
| Backend API | 8107 | http://localhost:8107 |
| API Docs (Swagger) | 8107 | http://localhost:8107/docs |
| Dashboard | 3107 | http://localhost:3107 |
| Landing Page | 3207 | http://localhost:3207 |
| PostgreSQL | 5507 | `postgresql://dropship:dropship_dev@db:5507/dropshipping` |
| Redis | 6407 | `redis://localhost:6407/0` |

---

## Environment Variables

Create a `.env` file in the `adscale/` directory:

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://dropship:dropship_dev@db:5507/dropshipping` | Async PostgreSQL connection string |
| `DATABASE_URL_SYNC` | `postgresql://dropship:dropship_dev@db:5507/dropshipping` | Sync PostgreSQL connection (Alembic) |

### Redis & Celery

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6407/0` | Redis connection for cache |
| `CELERY_BROKER_URL` | `redis://redis:6407/1` | Celery broker (Redis) |
| `CELERY_RESULT_BACKEND` | `redis://redis:6407/2` | Celery result backend (Redis) |

### Authentication

| Variable | Required | Description |
|----------|----------|-------------|
| `JWT_SECRET_KEY` | Yes | Secret for signing JWT tokens |
| `API_KEY_SECRET` | Yes | Secret for hashing API keys |

### Billing (Stripe)

| Variable | Required | Description |
|----------|----------|-------------|
| `STRIPE_SECRET_KEY` | No | Stripe API key for billing (mock mode if empty) |
| `STRIPE_PRO_PRICE_ID` | No | Stripe Price ID for Pro tier |
| `STRIPE_ENTERPRISE_PRICE_ID` | No | Stripe Price ID for Enterprise tier |
| `STRIPE_WEBHOOK_SECRET` | No | Stripe webhook signing secret |

### Frontend

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8107` | Dashboard → Backend URL |

### Example `.env` File

```bash
# Database
DATABASE_URL=postgresql+asyncpg://dropship:dropship_dev@db:5507/dropshipping
DATABASE_URL_SYNC=postgresql://dropship:dropship_dev@db:5507/dropshipping

# Redis
REDIS_URL=redis://redis:6407/0
CELERY_BROKER_URL=redis://redis:6407/1
CELERY_RESULT_BACKEND=redis://redis:6407/2

# Auth
JWT_SECRET_KEY=your-secret-key-here
API_KEY_SECRET=your-api-key-secret-here

# Stripe (optional)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PRO_PRICE_ID=price_...
STRIPE_ENTERPRISE_PRICE_ID=price_...

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8107
```

---

## Installation & Startup

### Quick Start

```bash
# From the adscale/ directory
make install && make migrate && make start
```

This will:
1. Install Python dependencies (`backend/requirements.txt`)
2. Install Node.js dependencies (`dashboard/package.json`, `landing/package.json`)
3. Run Alembic migrations to create database tables
4. Start all services via `docker-compose up`

### Step-by-Step

#### 1. Install Dependencies

```bash
# Backend (Python)
cd backend
pip install -r requirements.txt

# Dashboard (Node.js)
cd ../dashboard
npm install

# Landing Page (Node.js)
cd ../landing
npm install
```

#### 2. Run Database Migrations

```bash
cd backend
alembic upgrade head
```

#### 3. Start Services

**Option A: Docker Compose (Recommended)**

```bash
# From adscale/ directory
docker-compose up -d
```

**Option B: Local Development**

```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload --port 8107

# Terminal 2: Dashboard
cd dashboard
npm run dev

# Terminal 3: Landing Page
cd landing
npm run dev

# Terminal 4: Celery Worker (optional)
cd backend
celery -A app.tasks.celery_app worker --loglevel=info
```

---

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make install` | Install all dependencies (Python + Node.js) |
| `make migrate` | Run Alembic migrations |
| `make start` | Start all services via docker-compose |
| `make stop` | Stop all services |
| `make logs` | View service logs |
| `make test-backend` | Run all backend tests |
| `make clean` | Remove build artifacts and caches |

---

## Verifying Installation

### 1. Check API Health

```bash
curl http://localhost:8107/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "adscale",
  "timestamp": "2026-02-14T12:34:56.789Z"
}
```

### 2. Check API Documentation

Visit http://localhost:8107/docs to see the interactive Swagger UI.

### 3. Check Dashboard

Visit http://localhost:3107 to see the dashboard login page.

### 4. Check Landing Page

Visit http://localhost:3207 to see the marketing landing page.

---

## Development Workflow

### Running Tests

```bash
# All backend tests (164 tests)
make test-backend

# Verbose output
cd backend && pytest -v

# Specific test file
cd backend && pytest tests/test_campaigns.py -v

# Specific test
cd backend && pytest tests/test_campaigns.py::test_create_campaign_success -v
```

### Applying Schema Changes

```bash
# 1. Modify models in backend/app/models/
# 2. Generate migration
cd backend
alembic revision --autogenerate -m "description"

# 3. Review migration in backend/alembic/versions/
# 4. Apply migration
alembic upgrade head
```

### Adding New Dependencies

**Python:**
```bash
cd backend
pip install <package>
pip freeze > requirements.txt
```

**Node.js (Dashboard):**
```bash
cd dashboard
npm install <package>
```

**Node.js (Landing):**
```bash
cd landing
npm install <package>
```

---

## Troubleshooting

### Backend Won't Start

**Symptom:** `sqlalchemy.exc.OperationalError: could not connect to server`

**Solution:** Ensure PostgreSQL is running on port 5507.

```bash
docker-compose ps
docker-compose up -d db
```

### Migrations Fail

**Symptom:** `alembic.util.exc.CommandError: Target database is not up to date`

**Solution:** Reset migrations or upgrade to head.

```bash
cd backend
alembic downgrade base
alembic upgrade head
```

### Dashboard Can't Connect to API

**Symptom:** Dashboard shows "Network Error" or "Failed to fetch"

**Solution:** Verify `NEXT_PUBLIC_API_URL` is set correctly and the backend is running.

```bash
curl http://localhost:8107/health
```

### Port Conflicts

**Symptom:** `Error: Port 8107 is already in use`

**Solution:** Stop conflicting services or change ports in `docker-compose.yml`.

```bash
lsof -ti:8107 | xargs kill -9
```

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
