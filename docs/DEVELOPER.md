# Developer Guide

## Project Overview

The Dropshipping Platform is a multi-tenant SaaS application that lets users create and manage automated dropshipping stores. It consists of three applications:

- **Backend** — FastAPI REST API (Python 3.12)
- **Dashboard** — Admin interface for store owners (Next.js 16 + Shadcn/ui)
- **Storefront** — Customer-facing store (Next.js 16 + Tailwind)

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend framework | FastAPI | 0.115+ |
| ORM | SQLAlchemy (async) | 2.0+ |
| Database | PostgreSQL | 16 |
| Migrations | Alembic (async) | 1.14+ |
| Task queue | Celery + Redis | 5.4+ |
| Auth | python-jose (JWT) + bcrypt | — |
| Frontend framework | Next.js (App Router) | 16 |
| UI components | Shadcn/ui (dashboard only) | — |
| Styling | Tailwind CSS | 4 |
| Language | TypeScript | 5+ |

## Local Development Setup

### Prerequisites

- VS Code with the Dev Containers extension
- Docker Desktop running

### Starting the Environment

1. Open the project root in VS Code
2. Command Palette → **Dev Containers: Reopen in Container**
3. The container installs Python and Node dependencies automatically via `postCreateCommand`

### Services

All services run in the devcontainer. Open a separate terminal for each:

```bash
# Backend API — http://localhost:8000
cd /workspaces/ecomm/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Dashboard — http://localhost:3000
cd /workspaces/ecomm/dashboard
npm run dev

# Storefront — http://localhost:3001
cd /workspaces/ecomm/storefront
npm run dev -- -p 3001

# Celery worker
cd /workspaces/ecomm/backend
celery -A app.tasks.celery_app worker --loglevel=info

# Celery Beat (scheduler)
cd /workspaces/ecomm/backend
celery -A app.tasks.celery_app beat --loglevel=info

# Flower (task monitor, optional) — http://localhost:5555
cd /workspaces/ecomm/backend
celery -A app.tasks.celery_app flower --port=5555
```

### Ports

| Port | Service |
|------|---------|
| 8000 | Backend API |
| 3000 | Dashboard |
| 3001 | Storefront |
| 5432 | PostgreSQL |
| 6379 | Redis |
| 5555 | Flower |

### Environment Variables

Pre-configured in `.devcontainer/docker-compose.yml`:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | `postgresql+asyncpg://dropship:dropship_dev@db:5432/dropshipping` |
| `DATABASE_URL_SYNC` | `postgresql://dropship:dropship_dev@db:5432/dropshipping` |
| `REDIS_URL` | `redis://redis:6379/0` |
| `CELERY_BROKER_URL` | `redis://redis:6379/1` |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/2` |

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app + router registration
│   ├── config.py            # pydantic-settings (reads env vars)
│   ├── database.py          # Async engine, session factory, Base
│   ├── api/                 # FastAPI routers
│   │   ├── health.py        # GET /api/v1/health
│   │   ├── auth.py          # Auth endpoints (register, login, refresh, me)
│   │   └── deps.py          # Shared dependencies (get_current_user)
│   ├── models/              # SQLAlchemy models
│   │   └── user.py          # User model
│   ├── schemas/             # Pydantic request/response schemas
│   │   └── auth.py          # Auth request/response schemas
│   ├── services/            # Business logic
│   │   └── auth_service.py  # Password hashing, JWT, user registration/login
│   ├── tasks/               # Celery tasks
│   │   └── celery_app.py    # Celery instance + config
│   └── utils/               # Shared utilities
├── alembic/                 # Database migrations
│   ├── env.py               # Async migration environment
│   └── versions/            # Migration files
├── tests/
│   ├── conftest.py          # httpx AsyncClient fixture + DB isolation
│   ├── test_health.py       # Health endpoint test
│   └── test_auth.py         # Auth endpoint tests (15 tests)
└── pyproject.toml           # Dependencies + pytest/ruff config

dashboard/
├── src/
│   ├── app/                 # App Router pages
│   │   ├── layout.tsx       # Root layout (Geist fonts)
│   │   ├── page.tsx         # Home page
│   │   └── globals.css      # Tailwind + Shadcn/ui CSS vars
│   └── lib/
│       ├── api.ts           # API client (fetch wrapper with JWT)
│       └── utils.ts         # cn() class merge utility
├── components.json          # Shadcn/ui config
└── package.json

storefront/
├── src/
│   ├── app/                 # App Router pages
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
│   └── lib/
│       └── api.ts           # API client (fetch wrapper, no auth)
└── package.json
```

## Database Migrations

```bash
cd /workspaces/ecomm/backend

# Create a new migration after model changes
alembic revision --autogenerate -m "description of changes"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# See current migration state
alembic current
```

Alembic is configured for async via `asyncpg`. The `env.py` imports `Base.metadata` from `app.database` so autogenerate detects model changes.

## Testing

```bash
cd /workspaces/ecomm/backend

# Run all tests
pytest

# Verbose output
pytest -v

# Specific file
pytest tests/test_health.py
```

Tests use `pytest-asyncio` with `asyncio_mode = "auto"`. The `client` fixture in `conftest.py` provides an `httpx.AsyncClient` wired to the FastAPI app via `ASGITransport`. A `clean_tables` autouse fixture truncates all tables between tests for isolation (uses `NullPool` to avoid async connection conflicts).

### Writing a new test

```python
# tests/test_example.py
import pytest

@pytest.mark.asyncio
async def test_something(client):
    response = await client.get("/api/v1/some-endpoint")
    assert response.status_code == 200
```

## Code Quality

- **Python**: Ruff (configured in `pyproject.toml`, line-length=100, target py312)
- **TypeScript**: ESLint + Prettier (auto-format on save in VS Code)

## API Conventions

- All endpoints prefixed with `/api/v1/`
- Auth header: `Authorization: Bearer <jwt>`
- Success response: `{ "data": ..., "error": null }`
- Error response: `{ "data": null, "error": { "code": "...", "message": "..." } }`
- Pagination: `?page=1&per_page=20` → response includes `total`, `page`, `per_page`
- Store-scoped routes: `/api/v1/stores/{store_id}/products`
- Public routes (no auth): `/api/v1/public/...`
- Auto-generated docs: Swagger UI at `/docs`, ReDoc at `/redoc`
