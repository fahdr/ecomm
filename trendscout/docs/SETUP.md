# TrendScout Setup Guide

> Part of [TrendScout](README.md) documentation

This guide covers local development setup, prerequisites, environment configuration, and service startup procedures.

---

## Prerequisites

| Requirement | Version |
|------------|---------|
| Python | 3.12+ |
| Node.js | 20+ |
| PostgreSQL | 16 |
| Redis | 7 |
| Docker (optional) | Latest |

---

## Install Dependencies

### Backend

```bash
cd trendscout/backend
pip install -r requirements.txt
```

### Dashboard

```bash
cd trendscout/dashboard
npm install
```

### Landing Page

```bash
cd trendscout/landing
npm install
```

---

## Environment Variables

Create a `.env` file in the service root with the following configuration:

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_NAME` | `trendscout` | Internal service identifier |
| `SERVICE_DISPLAY_NAME` | `TrendScout` | Human-readable product name |
| `SERVICE_PORT` | `8101` | Backend listening port |
| `DEBUG` | `false` | Enable debug mode with SQL logging |
| `DATABASE_URL` | `postgresql+asyncpg://trendscout:trendscout_dev@localhost:5432/trendscout` | Async PostgreSQL connection |
| `DATABASE_URL_SYNC` | `postgresql://trendscout:trendscout_dev@localhost:5432/trendscout` | Sync connection (Alembic, Celery) |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis cache URL |
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | Celery task broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | Celery result store |
| `JWT_SECRET_KEY` | `dev-secret-change-in-production` | JWT signing secret |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token TTL |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |
| `CORS_ORIGINS` | `http://localhost:3101` | Comma-separated allowed origins |
| `STRIPE_SECRET_KEY` | (empty = mock mode) | Stripe API secret |
| `STRIPE_WEBHOOK_SECRET` | (empty) | Stripe webhook signing secret |
| `STRIPE_PRO_PRICE_ID` | (empty) | Stripe Price ID for Pro tier |
| `STRIPE_ENTERPRISE_PRICE_ID` | (empty) | Stripe Price ID for Enterprise tier |
| `STRIPE_BILLING_SUCCESS_URL` | `http://localhost:3101/billing?success=true` | Post-checkout redirect |
| `STRIPE_BILLING_CANCEL_URL` | `http://localhost:3101/billing?canceled=true` | Checkout cancel redirect |
| `ANTHROPIC_API_KEY` | (empty = mock analysis) | Anthropic API key for Claude |

---

## Database Migrations

```bash
# Generate a new migration after model changes
cd trendscout/backend
alembic revision --autogenerate -m "description of changes"

# Apply all pending migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# View migration history
alembic history

# Handle multiple heads (parallel migration branches)
alembic merge heads -m "merge heads"
alembic upgrade head
```

---

## Start Services

### Quick Start (All Services)

```bash
# From service root
make install
make migrate
make start
```

### Individual Services

#### Backend API (Port 8101)

```bash
cd trendscout/backend
uvicorn app.main:app --host 0.0.0.0 --port 8101 --reload
```

Access Swagger documentation at http://localhost:8101/docs

#### Celery Worker

```bash
cd trendscout/backend
celery -A app.tasks.celery_app worker -l info -Q trendscout
```

#### Dashboard (Port 3101)

```bash
cd trendscout/dashboard
npm run dev -- -p 3101
```

Access the dashboard at http://localhost:3101

#### Landing Page (Port 3201)

```bash
cd trendscout/landing
npm run dev -- -p 3201
```

Access the landing page at http://localhost:3201

---

## Docker

```bash
# From service root
docker-compose up
```

This starts all services in containers with proper networking and volume mounts.

---

## Services Table

| Service | Command | Port | Access |
|---------|---------|------|--------|
| Backend API | `uvicorn app.main:app --port 8101` | 8101 | http://localhost:8101 |
| Dashboard | `npm run dev -- -p 3101` | 3101 | http://localhost:3101 |
| Landing Page | `npm run dev -- -p 3201` | 3201 | http://localhost:3201 |
| PostgreSQL | Docker / system service | 5501 | N/A |
| Redis | Docker / system service | 6401 | N/A |
| Celery Worker | `celery -A app.tasks.celery_app worker -Q trendscout` | -- | N/A |

---

## Ports Table

| Port | Service | Description |
|------|---------|-------------|
| 8101 | Backend API | FastAPI server, Swagger at `/docs`, ReDoc at `/redoc` |
| 3101 | Dashboard | Next.js App Router dashboard for users |
| 3201 | Landing Page | Next.js static marketing/landing site |
| 5501 | PostgreSQL | Database server |
| 6401 | Redis | Cache, Celery broker, and result backend |

---

## Verification

After starting services, verify they are running correctly:

```bash
# Check backend health
curl http://localhost:8101/api/v1/health

# Check Swagger docs load
open http://localhost:8101/docs

# Check dashboard loads
open http://localhost:3101

# Check landing page loads
open http://localhost:3201
```

---

*See also: [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
