# SourcePilot

> Automated Supplier Product Import

## Overview

SourcePilot is an independently hostable SaaS product that provides automated supplier product import.
It can be used standalone or integrated with the dropshipping platform.

## Architecture

| Component | Technology | Port |
|-----------|-----------|------|
| Backend API | FastAPI + SQLAlchemy 2.0 | 8109 |
| Dashboard | Next.js 16 + Tailwind | 3109 |
| Landing Page | Next.js 16 (static) | 3209 |
| Database | PostgreSQL 16 | 5432 |
| Cache/Queue | Redis 7 | 6379 |
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
- **API**: http://localhost:8109
- **API Docs**: http://localhost:8109/docs
- **Dashboard**: http://localhost:3109
- **Landing Page**: http://localhost:3209

## API Authentication

### JWT Bearer Token
```bash
# Register
curl -X POST http://localhost:8109/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Use token
curl http://localhost:8109/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### API Key
```bash
# Create API key (requires JWT auth)
curl -X POST http://localhost:8109/api/v1/api-keys \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Integration", "scopes": ["read", "write"]}'

# Use API key
curl http://localhost:8109/api/v1/usage \
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
