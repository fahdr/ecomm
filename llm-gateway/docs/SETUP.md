# LLM Gateway Setup

> Part of [LLM Gateway](README.md) documentation

Complete environment setup for local development and testing.

## Prerequisites

- **Python** 3.11+
- **PostgreSQL** 14+ (shared ecomm database)
- **Redis** 6.2+ (for caching and rate limiting)
- **Docker** (if using devcontainer)

## Environment Variables

Create a `.env` file in `llm-gateway/backend/`:

```bash
# Service Configuration
LLM_GATEWAY_SERVICE_NAME=llm-gateway
LLM_GATEWAY_SERVICE_PORT=8200
LLM_GATEWAY_DEBUG=false

# Database (shared with other services)
LLM_GATEWAY_DATABASE_URL=postgresql+asyncpg://dropship:dropship_dev@db:5432/dropshipping

# Redis (dedicated DB for gateway)
LLM_GATEWAY_REDIS_URL=redis://redis:6379/3

# Service Authentication
LLM_GATEWAY_SERVICE_KEY=dev-gateway-key

# Cache and Rate Limiting
LLM_GATEWAY_CACHE_TTL_SECONDS=3600
LLM_GATEWAY_MAX_RETRIES=2

# Default Provider
LLM_GATEWAY_DEFAULT_PROVIDER=claude
LLM_GATEWAY_DEFAULT_MODEL=claude-sonnet-4-5-20250929
```

## Port Allocation

| Service | Port |
|---------|------|
| LLM Gateway Backend | 8200 |
| PostgreSQL | 5432 |
| Redis | 6379 |

## Installation

### 1. Install Dependencies

```bash
cd /workspaces/ecomm/llm-gateway/backend
pip install -r requirements.txt
```

### 2. Database Setup

The gateway creates its own tables on startup:

```python
# Tables created automatically:
# - llm_provider_configs
# - llm_customer_overrides
# - llm_usage_logs
```

All tables are prefixed with `llm_` to avoid collisions with other services.

### 3. Configure Providers

Providers are managed via the API or admin dashboard. To add a provider:

```bash
curl -X POST http://localhost:8200/api/v1/providers \
  -H "X-Service-Key: dev-gateway-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "claude",
    "display_name": "Anthropic Claude",
    "api_key": "sk-ant-api03-...",
    "models": [
      "claude-sonnet-4-5-20250929",
      "claude-3-5-haiku-20241022",
      "claude-opus-4-6"
    ],
    "is_enabled": true,
    "rate_limit_rpm": 60,
    "rate_limit_tpm": 100000,
    "priority": 10
  }'
```

## Running the Service

### Development Mode

```bash
cd /workspaces/ecomm/llm-gateway/backend
uvicorn app.main:app --host 0.0.0.0 --port 8200 --reload
```

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8200 --workers 4
```

### Health Check

```bash
curl http://localhost:8200/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "llm-gateway",
  "database": "connected"
}
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_generate.py -v

# Run with logs
pytest -v -s
```

## Development Tips

### 1. Schema Isolation

Tests use a dedicated `llm_gateway_test` schema. Each test truncates tables for full isolation.

### 2. Redis Cache

Cache keys are hashed from `(provider, model, prompt, system, temperature, json_mode)`. Clear cache between tests:

```bash
redis-cli -n 3 FLUSHDB
```

### 3. Rate Limiting

Rate limits use Redis counters with 60-second TTL. Override in tests:

```python
from app.services import rate_limit_service
rate_limit_service._redis_client = None  # Reset singleton
```

### 4. Mock Providers

For testing without real API calls, use the `custom` provider with a mock endpoint:

```python
config = ProviderConfig(
    name="custom",
    api_key="test-key",
    base_url="http://localhost:9999/mock",
    models=["mock-model"],
)
```

## Troubleshooting

### Database Connection Issues

```bash
# Verify PostgreSQL is running
docker ps | grep db

# Check connection
psql postgresql://dropship:dropship_dev@localhost:5432/dropshipping -c "SELECT 1"
```

### Redis Connection Issues

```bash
# Verify Redis is running
docker ps | grep redis

# Check connection
redis-cli -h localhost -p 6379 -n 3 PING
```

### Port Conflicts

```bash
# Check if port 8200 is in use
lsof -i :8200

# Kill the process
kill -9 <PID>
```

---

*See also: [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
