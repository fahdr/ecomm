# ShopChat Setup Guide

> Part of [ShopChat](README.md) documentation

This guide covers local development setup for the ShopChat AI Shopping Assistant service.

---

## Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for dashboard/landing development)
- Python 3.11+ (for backend development)
- Make (for build automation)

---

## Ports

| Service | Port | Description |
|---------|------|-------------|
| Backend API | `8108` | FastAPI server, Swagger docs at `/docs` |
| Dashboard | `3108` | Next.js dashboard UI |
| Landing Page | `3208` | Static marketing page |
| PostgreSQL | `5508` | Database |
| Redis | `6408` | Cache and Celery broker |

---

## Environment Variables

Create a `.env` file in the service root with these variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL async connection string | `postgresql+asyncpg://shopchat:shopchat_dev@db:5508/shopchat` |
| `DATABASE_URL_SYNC` | PostgreSQL sync connection string (Alembic) | `postgresql://shopchat:shopchat_dev@db:5508/shopchat` |
| `REDIS_URL` | Redis connection string | `redis://redis:6408/0` |
| `CELERY_BROKER_URL` | Celery broker URL | `redis://redis:6408/1` |
| `CELERY_RESULT_BACKEND` | Celery result backend URL | `redis://redis:6408/2` |
| `SECRET_KEY` | JWT signing key | Generate with `openssl rand -hex 32` |
| `STRIPE_SECRET_KEY` | Stripe API key (optional, mock mode if empty) | `""` |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | `""` |
| `NEXT_PUBLIC_API_URL` | Backend URL for dashboard frontend | `http://localhost:8108` |

### Example .env File

```bash
DATABASE_URL=postgresql+asyncpg://shopchat:shopchat_dev@db:5508/shopchat
DATABASE_URL_SYNC=postgresql://shopchat:shopchat_dev@db:5508/shopchat
REDIS_URL=redis://redis:6408/0
CELERY_BROKER_URL=redis://redis:6408/1
CELERY_RESULT_BACKEND=redis://redis:6408/2
SECRET_KEY=your-secret-key-here
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
NEXT_PUBLIC_API_URL=http://localhost:8108
```

---

## Quick Start

### Full Stack (Docker Compose)

```bash
# Install dependencies, run migrations, and start all services
make install && make migrate && make start
```

This starts:
- PostgreSQL database on port 5508
- Redis on port 6408
- Backend API on port 8108
- Dashboard on port 3108
- Landing page on port 3208
- Celery worker for background tasks

### Access Points

- **API**: http://localhost:8108
- **API Docs (Swagger)**: http://localhost:8108/docs
- **Dashboard**: http://localhost:3108
- **Landing Page**: http://localhost:3208

---

## Development Workflows

### Backend Development

```bash
# Install Python dependencies
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start backend server (with auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8108

# Run tests
pytest -v

# Run specific test file
pytest tests/test_chatbots.py -v

# Run with coverage
pytest --cov=app --cov-report=html
```

### Dashboard Development

```bash
# Install Node.js dependencies
cd dashboard
npm install

# Start development server (with hot reload)
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

### Landing Page Development

```bash
# Install dependencies
cd landing
npm install

# Start development server
npm run dev

# Build static export
npm run build
```

---

## Database Management

### Migrations

```bash
# Create a new migration
cd backend
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

### Direct Database Access

```bash
# Connect to PostgreSQL
docker exec -it shopchat-db psql -U shopchat -d shopchat

# Useful queries
SELECT * FROM users;
SELECT * FROM chatbots WHERE user_id = 'uuid';
SELECT * FROM knowledge_base WHERE chatbot_id = 'uuid';
SELECT * FROM conversations WHERE status = 'active';
```

---

## Redis Management

```bash
# Connect to Redis CLI
docker exec -it shopchat-redis redis-cli

# Check keys
KEYS *

# Monitor real-time commands
MONITOR

# Flush all data (use with caution)
FLUSHALL
```

---

## Celery Task Queue

```bash
# Start Celery worker (from backend directory)
celery -A app.tasks.celery_app worker --loglevel=info

# Start Celery beat (scheduler for periodic tasks)
celery -A app.tasks.celery_app beat --loglevel=info

# Monitor tasks with Flower (web UI)
celery -A app.tasks.celery_app flower --port=5555
```

---

## Testing

### Backend Tests (113 tests)

```bash
# Run all tests
make test-backend

# Run from backend directory with verbose output
cd backend && pytest -v

# Run specific test file
cd backend && pytest tests/test_chatbots.py -v

# Run single test
cd backend && pytest tests/test_widget.py::test_widget_chat_basic -v

# Run with markers
cd backend && pytest -v -x    # stop on first failure
cd backend && pytest -v -k "chatbot"  # run only chatbot tests
```

### Test Database

Tests use a dedicated schema (`shopchat_test`) in the PostgreSQL database. The `setup_db` fixture creates tables before each test and truncates all tables with `CASCADE` after. This ensures test isolation without interfering with development data.

---

## Docker Compose Services

The `docker-compose.yml` orchestrates all services:

```yaml
services:
  db:          # PostgreSQL 16 on port 5508
  redis:       # Redis 7 on port 6408
  backend:     # FastAPI on port 8108
  worker:      # Celery worker
  dashboard:   # Next.js on port 3108
  landing:     # Next.js on port 3208
```

### Service Management

```bash
# Start all services
make start

# Stop all services
make stop

# View logs
docker-compose logs -f backend
docker-compose logs -f worker

# Restart a single service
docker-compose restart backend

# Rebuild after code changes
docker-compose up --build backend
```

---

## Troubleshooting

### Backend won't start

- Check `DATABASE_URL` is correct
- Ensure PostgreSQL is running: `docker-compose ps db`
- Check logs: `docker-compose logs backend`
- Verify migrations: `cd backend && alembic current`

### Dashboard shows connection error

- Verify `NEXT_PUBLIC_API_URL` points to backend (http://localhost:8108)
- Check backend is running: `curl http://localhost:8108/api/v1/health`
- Check browser console for CORS errors

### Tests failing

- Ensure test database schema exists: `SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'shopchat_test';`
- Terminate stale connections: `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'shopchat' AND application_name = 'pytest';`
- Check fixture setup in `conftest.py`

### Celery tasks not running

- Verify Redis is running: `docker-compose ps redis`
- Check worker logs: `docker-compose logs worker`
- Confirm broker URL: `echo $CELERY_BROKER_URL`

---

*See also: [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md) · [README](README.md)*
