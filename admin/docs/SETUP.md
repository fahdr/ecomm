# Setup Guide

> Part of [Admin Dashboard](README.md) documentation

Complete installation and configuration instructions for the Super Admin Dashboard.

## Prerequisites

**Backend:**
- Python 3.11+
- PostgreSQL 13+ (shared with platform, schema isolation)
- Redis 6+

**Dashboard:**
- Node.js 18+
- npm 9+

**Required Access:**
- PostgreSQL connection string
- Redis URL
- LLM Gateway URL and service key

## Port Assignments

| Service          | Port | Description                            |
|------------------|------|----------------------------------------|
| Admin Backend    | 8300 | FastAPI REST API                       |
| Admin Dashboard  | 3300 | Next.js frontend                       |
| PostgreSQL       | 5432 | Shared database (admin_* tables)       |
| Redis            | 6379 | Database 4 for admin sessions          |

## Environment Variables

### Backend (admin/backend)

Create a `.env` file or set these variables:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://dropship:dropship_dev@db:5432/dropshipping

# Redis (db 4 for admin)
REDIS_URL=redis://redis:6379/4

# LLM Gateway connection
LLM_GATEWAY_URL=http://localhost:8200
LLM_GATEWAY_KEY=dev-gateway-key

# Admin JWT secret (change in production)
ADMIN_SECRET_KEY=admin-super-secret-key-change-in-production
ADMIN_TOKEN_EXPIRE_MINUTES=480

# Service port
ADMIN_SERVICE_PORT=8300

# Debug mode (verbose SQL logging)
ADMIN_DEBUG=false
```

### Dashboard (admin/dashboard)

Create a `.env.local` file:

```bash
# Backend API URL
NEXT_PUBLIC_ADMIN_API_URL=http://localhost:8300/api/v1/admin
```

## Installation

### Backend

```bash
cd admin/backend

# Install dependencies
pip install -r requirements.txt

# Run database migrations (tables created on startup)
# No manual migrations needed — uses create_all() on startup

# Start the backend
uvicorn app.main:app --host 0.0.0.0 --port 8300
```

**Backend startup:**
- Creates `admin_users` and `admin_health_snapshots` tables if missing
- Uses `checkfirst=True` to avoid modifying existing tables
- Listens on `0.0.0.0:8300`

### Dashboard

```bash
cd admin/dashboard

# Install dependencies
npm install

# Start the dev server
npm run dev  # Runs on port 3300

# Build for production
npm run build
npm start
```

**Dashboard startup:**
- Runs on port 3300 by default
- Proxies API requests to backend at port 8300
- Supports hot reload during development

## Database Setup

The admin backend uses the **shared ecomm PostgreSQL database** with `admin_` prefixed tables to avoid collisions.

**Tables created on startup:**

1. **admin_users**
   - Stores platform admin accounts
   - Fields: id, email, hashed_password, role, is_active, timestamps

2. **admin_health_snapshots**
   - Records service health check history
   - Fields: id, service_name, status, response_time_ms, checked_at

**Schema isolation for tests:**
- Tests use the `admin_test` schema
- Raw asyncpg for schema creation/termination
- `search_path` set via SQLAlchemy connect event

## First-Time Setup

### 1. Create the first super_admin user

```bash
curl -X POST http://localhost:8300/api/v1/admin/auth/setup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "YourSecurePassword123"
  }'
```

**Response (201 Created):**
```json
{
  "id": "uuid-here",
  "email": "admin@example.com",
  "role": "super_admin",
  "is_active": true
}
```

**Important:** The setup endpoint only works once. After the first admin is created, subsequent calls return 409 Conflict.

### 2. Log in to get a JWT token

```bash
curl -X POST http://localhost:8300/api/v1/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "YourSecurePassword123"
  }'
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

**Token details:**
- Expires after 480 minutes (8 hours) by default
- Signed with `ADMIN_SECRET_KEY`
- Contains `sub` (admin user ID) and `exp` (expiration timestamp)

### 3. Access the dashboard

Navigate to `http://localhost:3300` and log in with your credentials.

## Service Configuration

The backend is configured to monitor 9 services by default. Edit `admin/backend/app/config.py` to add or remove services:

```python
service_urls: dict[str, str] = {
    "llm-gateway": "http://localhost:8200",
    "trendscout": "http://localhost:8101",
    "contentforge": "http://localhost:8102",
    # ... add more services
}
```

## Troubleshooting

**Backend won't start:**
- Check DATABASE_URL is correct and PostgreSQL is running
- Check Redis is running on the configured port
- Ensure port 8300 is not already in use

**Dashboard shows "Cannot connect to backend":**
- Verify backend is running on port 8300
- Check `NEXT_PUBLIC_ADMIN_API_URL` in `.env.local`
- Check browser console for CORS errors

**Setup endpoint returns 409:**
- An admin user already exists
- Use `/auth/login` instead
- To reset, manually delete from `admin_users` table

**Health checks show all services "down":**
- Services may not be running
- Check service URLs in `config.py` are correct
- Verify each service's `/api/v1/health` endpoint responds

**Tests fail with schema errors:**
- Ensure `admin_test` schema isolation is working
- Check `conftest.py` search_path configuration
- Run `pytest -v` to see detailed failures

---
*See also: [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md) · [End User Guide](END_USER.md)*
