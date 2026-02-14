# {{SERVICE_DISPLAY_NAME}}

> {{SERVICE_TAGLINE}}

## Overview

{{SERVICE_DISPLAY_NAME}} is an independently hostable SaaS product that provides {{SERVICE_TAGLINE_LOWER}}.
It can be used standalone or integrated with the dropshipping platform.

## Architecture

| Component | Technology | Port |
|-----------|-----------|------|
| Backend API | FastAPI + SQLAlchemy 2.0 | {{SERVICE_PORT}} |
| Dashboard | Next.js 16 + Tailwind | {{DASHBOARD_PORT}} |
| Landing Page | Next.js 16 (static) | {{LANDING_PORT}} |
| Database | PostgreSQL 16 | {{DB_PORT}} |
| Cache/Queue | Redis 7 | {{REDIS_PORT}} |
| Task Queue | Celery | — |

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20+
- PostgreSQL 16
- Redis 7

### Local Development

```bash
# Install dependencies
make install

# Run database migrations
make migrate

# Start all services
make start
```

### Docker

```bash
docker-compose up
```

### Access Points
- **API**: http://localhost:{{SERVICE_PORT}}
- **API Docs**: http://localhost:{{SERVICE_PORT}}/docs
- **Dashboard**: http://localhost:{{DASHBOARD_PORT}}
- **Landing Page**: http://localhost:{{LANDING_PORT}}

## API Authentication

### JWT Bearer Token
```bash
# Register
curl -X POST http://localhost:{{SERVICE_PORT}}/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Use token
curl http://localhost:{{SERVICE_PORT}}/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### API Key
```bash
# Create API key (requires JWT auth)
curl -X POST http://localhost:{{SERVICE_PORT}}/api/v1/api-keys \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Integration", "scopes": ["read", "write"]}'

# Use API key
curl http://localhost:{{SERVICE_PORT}}/api/v1/usage \
  -H "X-API-Key: <api_key>"
```

## Pricing

| Tier | Price/mo | Description |
|------|----------|-------------|
| Free | $0 | Limited usage for evaluation |
| Pro | $XX | Full features for professionals |
| Enterprise | $XX | Unlimited + API access |

## Testing

```bash
make test-backend    # Backend unit tests
```

## Environment Variables

See `.env.example` for all available configuration options.

## License

Proprietary — All rights reserved.
