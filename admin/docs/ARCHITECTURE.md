# Architecture

> Part of [Admin Dashboard](README.md) documentation

Technical architecture, design decisions, and system structure for the Super Admin Dashboard.

## Tech Stack

**Backend:**
- FastAPI 0.100+ (async REST API)
- SQLAlchemy 2.0 (async ORM with asyncpg driver)
- Pydantic 2.0 (request/response validation)
- bcrypt (password hashing)
- PyJWT (admin authentication tokens)
- httpx (async HTTP client for service pings)

**Dashboard:**
- Next.js 14+ (React 18+ with App Router)
- TypeScript 5+
- Motion (framer-motion) for animations
- Lucide React (icon library)
- CSS variables for theming

**Infrastructure:**
- PostgreSQL 13+ (shared database with `admin_` table prefix)
- Redis 6+ (database 4 for admin session cache)
- Docker Compose (development environment)

## Project Structure

```
admin/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py             # Admin login, setup, profile
│   │   │   ├── health_monitor.py   # Service health checks
│   │   │   ├── llm_proxy.py        # LLM Gateway proxy (providers, usage)
│   │   │   ├── services_overview.py # Service listing
│   │   │   └── deps.py             # get_current_admin dependency
│   │   ├── models/
│   │   │   ├── admin_user.py       # Admin account ORM model
│   │   │   └── health_snapshot.py  # Health check history ORM model
│   │   ├── services/
│   │   │   └── auth_service.py     # JWT creation, bcrypt hashing
│   │   ├── config.py               # Settings (service URLs, secrets)
│   │   ├── database.py             # Async engine, session factory
│   │   └── main.py                 # FastAPI app, router mounting
│   ├── tests/
│   │   ├── conftest.py             # Fixtures (schema isolation)
│   │   ├── test_auth.py            # 201 lines (login, setup, me)
│   │   ├── test_health_monitor.py  # 253 lines (ping, history)
│   │   ├── test_llm_proxy.py       # 344 lines (providers, usage)
│   │   └── test_services_overview.py # 195 lines (service list)
│   └── requirements.txt
├── dashboard/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx            # Overview (KPIs, health grid)
│   │   │   ├── providers/page.tsx  # Provider CRUD
│   │   │   ├── costs/page.tsx      # Usage cost analytics
│   │   │   ├── services/page.tsx   # Service status list
│   │   │   └── login/page.tsx      # Admin login form
│   │   ├── components/
│   │   │   ├── admin-shell.tsx     # Layout wrapper
│   │   │   └── status-badge.tsx    # Health status indicator
│   │   └── lib/
│   │       ├── api.ts              # Admin API client
│   │       └── auth.ts             # Token storage, logout
│   ├── next.config.ts
│   ├── package.json
│   └── tsconfig.json
└── docs/                           # This documentation
```

## Authentication Flow

**Admin authentication is separate from platform customer auth.**

1. **First-time setup:**
   - Call `POST /auth/setup` (only works when no admins exist)
   - Creates a `super_admin` account with bcrypt-hashed password

2. **Login:**
   - Call `POST /auth/login` with email/password
   - Backend verifies bcrypt hash
   - Returns JWT signed with `ADMIN_SECRET_KEY`
   - Token expires after `ADMIN_TOKEN_EXPIRE_MINUTES` (default 480 = 8 hours)

3. **Authenticated requests:**
   - Dashboard stores JWT in localStorage
   - Sends `Authorization: Bearer <token>` header
   - Backend validates JWT via `get_current_admin` dependency
   - Dependency loads `AdminUser` from database and checks `is_active`

**Admin roles:**
- `super_admin` — Full access (setup creates this)
- `admin` — Standard access (future)
- `viewer` — Read-only access (future)

Role-based access control is not yet enforced; all authenticated admins have full access.

## Service Health Monitoring

### Real-Time Health Checks

The `GET /health/services` endpoint pings all configured services concurrently:

1. Reads service URLs from `settings.service_urls` (9 services)
2. Uses `asyncio.gather` with httpx to ping `/api/v1/health` on each service
3. Classifies responses:
   - **healthy:** HTTP 200 with `{"status": "healthy"}` body
   - **degraded:** HTTP 200 but non-healthy status, or non-200 response
   - **down:** Timeout, connection error, or exception
4. Persists a `ServiceHealthSnapshot` row for each service
5. Returns aggregated results with response times

**Timeout:** 5 seconds per service (configurable via `HEALTH_CHECK_TIMEOUT`)

### Health History

The `GET /health/history` endpoint queries stored snapshots:

- Defaults to last 50 snapshots across all services
- Supports `service_name` filter for a specific service
- Supports `limit` parameter (1-500)
- Ordered by `checked_at` descending (most recent first)

Use cases:
- Uptime trends over time
- Latency tracking per service
- Alerting on repeated failures

## LLM Gateway Proxy Pattern

The admin backend **proxies all LLM Gateway management endpoints** rather than directly accessing the gateway's database. This maintains separation of concerns.

### Proxy Endpoints

**Providers:**
- `GET /llm/providers` → `GET /api/v1/providers` on gateway
- `POST /llm/providers` → `POST /api/v1/providers` on gateway
- `PATCH /llm/providers/:id` → `PATCH /api/v1/providers/:id` on gateway
- `DELETE /llm/providers/:id` → `DELETE /api/v1/providers/:id` on gateway

**Usage Analytics:**
- `GET /llm/usage/summary` → `GET /api/v1/usage/summary` on gateway
- `GET /llm/usage/by-provider` → `GET /api/v1/usage/by-provider` on gateway
- `GET /llm/usage/by-service` → `GET /api/v1/usage/by-service` on gateway

**Authentication:**
- Admin backend adds `X-Service-Key: {LLM_GATEWAY_KEY}` header to all proxied requests
- Gateway validates the service key before processing
- Timeout for proxy requests: 10 seconds

### Why Proxy Instead of Direct DB Access?

1. **Separation of concerns:** Gateway owns its data model
2. **API stability:** Gateway's endpoints are the contract; tables can change
3. **Authorization:** Service key is easier to rotate than DB credentials
4. **Observability:** Gateway can log admin operations separately

## Dashboard UI Patterns

### Page Structure

All pages use `<AdminShell>` wrapper:
- Sidebar navigation (Overview, Providers, Costs, Services)
- Top bar with logout button
- Page content area with motion animations

### Animations

Uses `motion` (framer-motion) for staggered fade-ins:
- Page headers: `initial={{ opacity: 0, y: -10 }}` with 0.4s duration
- Cards/rows: `initial={{ opacity: 0, y: 15 }}` with staggered delays (0.05s per item)

**Performance:** CSS variables for theming allow instant theme switching without component re-renders.

### Design System

**CSS Variables (globals.css):**
```css
--admin-primary: oklch(0.65 0.24 265);
--admin-accent: oklch(0.72 0.18 45);
--admin-success: oklch(0.68 0.18 145);
--admin-danger: oklch(0.63 0.22 25);
--admin-text-primary: oklch(0.98 0.02 265);
--admin-text-muted: oklch(0.65 0.05 265);
--admin-bg: oklch(0.12 0.04 265);
--admin-bg-surface: oklch(0.16 0.04 265);
--admin-border: oklch(0.24 0.05 265);
```

**Component classes:**
- `.admin-card` — Elevated panel with border and shadow
- `.admin-btn-primary` — Solid accent button
- `.admin-btn-ghost` — Transparent hover button
- `.admin-input` — Form input with focus ring
- `.admin-table` — Data table with hover rows

**Status badges:**
- `healthy` — Green with dot indicator
- `degraded` — Amber/yellow with dot indicator
- `down` — Red with dot indicator
- `unknown` — Gray with dot indicator

## Key Design Decisions

### 1. Shared Database with Table Prefix

**Decision:** Use the platform's PostgreSQL database with `admin_` prefixed tables instead of a separate database.

**Rationale:**
- Simplifies deployment (one less DB to manage)
- Admin data is low-volume (users, health snapshots)
- Table prefixes prevent collisions with other services
- Shared connection pooling benefits performance

**Test isolation:** Tests use the `admin_test` schema to avoid conflicts.

### 2. Proxy Pattern for LLM Gateway

**Decision:** Proxy gateway endpoints instead of direct database access.

**Rationale:**
- Gateway owns its schema; admin should not depend on internal tables
- Service key is easier to rotate than DB credentials
- Gateway can log and audit admin operations
- Maintains service boundaries

### 3. Separate Admin Authentication

**Decision:** Admin JWT is independent from platform customer JWT and gateway service key.

**Rationale:**
- Admin access is more sensitive (full platform control)
- Independent key rotation without affecting customers
- Different expiration policy (8 hours vs. platform's 24 hours)
- Clear separation of concerns

### 4. Session-Scoped Schema Creation in Tests

**Decision:** Use `pytest` session-scoped `create_tables` fixture with schema isolation.

**Rationale:**
- Faster tests (schema created once, tables truncated per test)
- Avoids schema creation race conditions
- Matches pattern used in other ecomm services
- Raw asyncpg for schema ops prevents SQLAlchemy metadata conflicts

### 5. No Alembic Migrations

**Decision:** Use `Base.metadata.create_all()` on startup instead of Alembic.

**Rationale:**
- Admin schema is simple (2 tables, no foreign keys)
- No production migration history needed yet
- Startup creation works for MVP
- Can add Alembic later if schema complexity grows

---
*See also: [Setup](SETUP.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md) · [QA Engineer Guide](QA_ENGINEER.md)*
