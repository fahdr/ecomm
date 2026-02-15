# FlowSend Setup Guide

> Part of [FlowSend](README.md) documentation

This guide covers local development environment setup, service ports, environment variables, and starting the FlowSend stack.

## Prerequisites

- **Docker** 24+ with Docker Compose
- **Node.js** 20+ with npm
- **Python** 3.12+
- **Make** (optional, for convenience commands)

## Port Assignments

| Component | Port | URL |
|-----------|------|-----|
| Backend API | 8104 | http://localhost:8104 |
| API Docs (Swagger) | 8104 | http://localhost:8104/docs |
| API Docs (ReDoc) | 8104 | http://localhost:8104/redoc |
| Dashboard | 3104 | http://localhost:3104 |
| Landing Page | 3204 | http://localhost:3204 |
| PostgreSQL | 5504 | `postgresql://dropship:dropship_dev@localhost:5504/flowsend` |
| Redis | 6404 | `redis://localhost:6404/0` |

## Quick Start

From the `flowsend/` directory:

```bash
# Install all dependencies
make install

# Run database migrations
make migrate

# Start all services (backend, dashboard, landing, DB, Redis, Celery)
make start
```

After starting, access the services:

- **Backend API**: http://localhost:8104
- **Swagger Docs**: http://localhost:8104/docs
- **Dashboard**: http://localhost:3104
- **Landing Page**: http://localhost:3204

## Individual Service Commands

### Backend

```bash
# Install Python dependencies
cd backend
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start backend API (development mode with auto-reload)
uvicorn app.main:app --host 0.0.0.0 --port 8104 --reload

# Start Celery worker
celery -A app.tasks.celery_app worker --loglevel=info
```

### Dashboard

```bash
# Install Node dependencies
cd dashboard
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

### Landing Page

```bash
# Install Node dependencies
cd landing
npm install

# Start development server
npm run dev

# Build static export
npm run build
```

## Environment Variables

Create a `.env` file in the `flowsend/` root directory with the following variables:

### Database

```bash
# Async connection for SQLAlchemy
DATABASE_URL=postgresql+asyncpg://dropship:dropship_dev@db:5504/flowsend

# Sync connection for Alembic migrations
DATABASE_URL_SYNC=postgresql://dropship:dropship_dev@db:5504/flowsend
```

### Redis

```bash
# Redis cache (DB 0)
REDIS_URL=redis://redis:6404/0

# Celery broker (DB 1)
CELERY_BROKER_URL=redis://redis:6404/1

# Celery result backend (DB 2)
CELERY_RESULT_BACKEND=redis://redis:6404/2
```

### Authentication

```bash
# JWT signing secret (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=<your-secret-key>

# Access token expiry in minutes (default: 30)
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Refresh token expiry in days (default: 7)
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

### Stripe (optional — leave empty for mock mode)

```bash
# Stripe API secret key (sk_test_...)
STRIPE_SECRET_KEY=

# Stripe webhook signature secret (whsec_...)
STRIPE_WEBHOOK_SECRET=

# Stripe Price IDs for each plan tier
STRIPE_PRO_PRICE_ID=
STRIPE_ENTERPRISE_PRICE_ID=
```

**Note**: If `STRIPE_SECRET_KEY` is empty, FlowSend runs in **mock billing mode** — subscriptions are created directly in the database without calling Stripe APIs. This is the default for development and testing.

### CORS (optional)

```bash
# Allowed origins for CORS (comma-separated)
CORS_ORIGINS=http://localhost:3104,http://localhost:3204
```

## Docker Compose

The `docker-compose.yml` file in the `flowsend/` directory defines the full stack:

```yaml
services:
  db:          # PostgreSQL 16 on port 5504
  redis:       # Redis 7 on port 6404
  backend:     # FastAPI on port 8104
  worker:      # Celery worker
  dashboard:   # Next.js on port 3104
  landing:     # Next.js on port 3204
```

### Start with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

## Database Setup

### Running Migrations

```bash
# From backend/ directory
cd backend

# View current migration status
alembic current

# View pending migrations
alembic history

# Upgrade to latest
alembic upgrade head

# Downgrade one revision
alembic downgrade -1
```

### Creating New Migrations

```bash
# Auto-generate from model changes
alembic revision --autogenerate -m "Add new table"

# Create empty migration
alembic revision -m "Custom migration"

# Apply the new migration
alembic upgrade head
```

## Service Configuration

### Backend Config

All backend configuration is loaded from environment variables via `backend/app/config.py`:

```python
class Settings:
    database_url: str
    redis_url: str
    jwt_secret_key: str
    stripe_secret_key: str = ""
    # ... etc
```

### Dashboard Config

Dashboard branding, navigation, and plans are defined in `dashboard/src/service.config.ts`:

```typescript
export const serviceConfig = {
  name: "FlowSend",
  tagline: "Smart Email Marketing",
  slug: "flowsend",
  apiUrl: "http://localhost:8104",
  colors: {
    primary: "oklch(0.65 0.20 25)",  // Coral Red
    accent: "oklch(0.75 0.18 40)",   // Orange
  },
  fonts: {
    heading: "Satoshi",
    body: "Source Sans 3",
  },
  // ... navigation, plans, etc.
}
```

Changing values in this file updates the entire dashboard without code changes.

## Troubleshooting

### Port Conflicts

If ports are already in use:

```bash
# Check what's using a port
lsof -i :8104

# Kill the process
kill -9 <PID>

# Or change ports in docker-compose.yml and .env
```

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps db

# View database logs
docker-compose logs db

# Connect to database manually
psql postgresql://dropship:dropship_dev@localhost:5504/flowsend
```

### Migration Conflicts

```bash
# If migrations are out of sync
alembic downgrade base
alembic upgrade head

# If autogenerate detects unwanted changes
# Review backend/app/models/__init__.py to ensure all models are exported
```

### Celery Not Processing Tasks

```bash
# Check worker logs
docker-compose logs worker

# Verify Redis connection
redis-cli -h localhost -p 6404 ping

# Restart worker
docker-compose restart worker
```

---

*See also: [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md) · [README](README.md)*
