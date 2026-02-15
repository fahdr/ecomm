# RankPilot Setup Guide

> Part of [RankPilot](README.md) documentation

This guide covers local development environment setup, prerequisites, port configuration, and service startup commands.

## Prerequisites

### Required Software

| Tool | Version | Purpose |
|------|---------|---------|
| Docker | 20.10+ | Container runtime |
| Docker Compose | 2.0+ | Multi-container orchestration |
| Make | 4.0+ | Build automation |
| Node.js | 20+ | Dashboard/landing development |
| Python | 3.12 | Backend development |

### Optional Tools

- **HTTPie** or **curl** -- API testing
- **pgAdmin** or **TablePlus** -- Database inspection
- **Redis Commander** -- Redis monitoring

## Port Configuration

RankPilot uses port base **103** for all services:

| Service | Port | Purpose |
|---------|------|---------|
| Backend API | **8103** | FastAPI application + Swagger docs at `/docs` |
| Dashboard | **3103** | Next.js 16 dashboard (App Router) |
| Landing Page | **3203** | Next.js 16 static marketing site |
| PostgreSQL | **5503** | Database |
| Redis | **6403** | Cache and Celery broker |

### Port Conflicts

If ports are already in use, edit `docker-compose.yml` to change the left side of port mappings:

```yaml
services:
  backend:
    ports:
      - "9103:8103"  # Changed external port to 9103
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

### Database Configuration

```bash
# Primary database URL (async for SQLAlchemy)
DATABASE_URL=postgresql+asyncpg://dropship:dropship_dev@db:5503/rankpilot

# Sync URL for Alembic migrations
DATABASE_URL_SYNC=postgresql://dropship:dropship_dev@db:5503/rankpilot
```

### Redis Configuration

```bash
# Cache and session storage
REDIS_URL=redis://redis:6403/0

# Celery task broker
CELERY_BROKER_URL=redis://redis:6403/1

# Celery result backend
CELERY_RESULT_BACKEND=redis://redis:6403/2
```

### Security Configuration

```bash
# JWT token signing (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### Stripe Configuration

```bash
# Leave empty for mock mode (no real API calls)
STRIPE_SECRET_KEY=""
STRIPE_WEBHOOK_SECRET=""

# Price IDs (set after creating products in Stripe)
STRIPE_PRO_PRICE_ID=""
STRIPE_ENTERPRISE_PRICE_ID=""
```

### Dashboard Configuration

```bash
# Backend API URL from Next.js perspective
NEXT_PUBLIC_API_URL=http://localhost:8103
```

## Installation

### Step 1: Clone and Navigate

```bash
cd /workspaces/ecomm/rankpilot
```

### Step 2: Install Dependencies

```bash
# Install backend Python dependencies
make install

# Or manually:
cd backend && pip install -r requirements.txt

# Install dashboard dependencies
cd dashboard && npm install

# Install landing page dependencies
cd landing && npm install
```

### Step 3: Run Migrations

```bash
# Apply all database migrations
make migrate

# Or manually:
cd backend && alembic upgrade head
```

### Step 4: Start Services

```bash
# Start all services (backend, dashboard, landing, DB, Redis)
make start

# Or start individual services:
docker-compose up backend        # Backend only
docker-compose up dashboard      # Dashboard only
docker-compose up landing        # Landing only
```

## Verification

### Backend API

```bash
# Health check
curl http://localhost:8103/api/v1/health

# Expected response:
# {
#   "status": "ok",
#   "service": "rankpilot",
#   "timestamp": "2025-01-01T00:00:00.000000"
# }

# Swagger UI
open http://localhost:8103/docs
```

### Dashboard

```bash
# Access dashboard
open http://localhost:3103

# Check logs
docker-compose logs -f dashboard
```

### Landing Page

```bash
# Access landing
open http://localhost:3203

# Check logs
docker-compose logs -f landing
```

### Database

```bash
# Connect with psql
docker-compose exec db psql -U dropship -d rankpilot

# List tables
\dt

# Expected tables:
# - users
# - subscriptions
# - api_keys
# - sites
# - blog_posts
# - keyword_tracking
# - seo_audits
# - schema_configs
```

### Redis

```bash
# Connect with redis-cli
docker-compose exec redis redis-cli

# Check connectivity
ping
# Expected: PONG
```

## Common Development Tasks

### Running Tests

```bash
# All backend tests (165 tests)
make test-backend

# Specific test file
pytest backend/tests/test_sites.py -v

# Specific test
pytest backend/tests/test_blog.py::test_create_blog_post_basic -v

# With print output
pytest backend/tests -v -s
```

### Database Operations

```bash
# Create new migration
cd backend
alembic revision --autogenerate -m "add new table"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# Reset database (drops all tables)
make db-reset
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f dashboard

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Restarting Services

```bash
# Restart all
make restart

# Restart specific service
docker-compose restart backend
docker-compose restart dashboard
```

### Stopping Services

```bash
# Stop all services
make stop

# Or:
docker-compose down

# Stop and remove volumes (DELETES DATA)
docker-compose down -v
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8103
lsof -i :8103

# Kill the process
kill -9 <PID>

# Or change port in docker-compose.yml
```

### Database Connection Errors

```bash
# Check if PostgreSQL is running
docker-compose ps db

# Restart database
docker-compose restart db

# Check logs
docker-compose logs db
```

### Migration Errors

```bash
# Drop all tables and recreate
docker-compose exec db psql -U dropship -d rankpilot -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Re-run migrations
cd backend && alembic upgrade head
```

### Redis Connection Errors

```bash
# Check if Redis is running
docker-compose ps redis

# Restart Redis
docker-compose restart redis

# Clear all data
docker-compose exec redis redis-cli FLUSHALL
```

### Dashboard Build Errors

```bash
# Clear Next.js cache
cd dashboard
rm -rf .next node_modules
npm install
```

## Development Workflow

### Typical Development Session

1. Start services: `make start`
2. Make code changes
3. Run tests: `make test-backend`
4. Check API docs: http://localhost:8103/docs
5. Test in dashboard: http://localhost:3103
6. Stop services: `make stop`

### Hot Reload

- **Backend**: Uvicorn auto-reloads on file changes
- **Dashboard**: Next.js Fast Refresh updates automatically
- **Database**: Requires migration + restart

### Adding New Features

1. Create model in `backend/app/models/`
2. Create service in `backend/app/services/`
3. Create API route in `backend/app/api/`
4. Write tests in `backend/tests/`
5. Generate migration: `alembic revision --autogenerate`
6. Apply migration: `alembic upgrade head`
7. Update dashboard if needed

---

*See also: [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
