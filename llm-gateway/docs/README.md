# LLM Gateway

> Part of [LLM Gateway](README.md) documentation

**Centralized AI inference proxy for all ecomm services**

The LLM Gateway is a FastAPI microservice that routes LLM requests from all 8 SaaS services through a single endpoint. It handles provider selection, response caching, rate limiting, and cost tracking — eliminating the need for each service to bundle 6+ AI SDK dependencies and manage API keys.

## Quick Start

```bash
# Start the gateway (port 8200)
cd /workspaces/ecomm/llm-gateway/backend
uvicorn app.main:app --host 0.0.0.0 --port 8200

# Run tests (42 tests)
pytest -v
```

## Service Metrics

| Metric | Value |
|--------|-------|
| **Port** | 8200 |
| **Tests** | 42 |
| **Database** | PostgreSQL (shared, `llm_*` tables) |
| **Cache** | Redis (db 3) |
| **Providers** | Claude, OpenAI, Gemini, Llama, Mistral, Custom |

## Documentation Index

| Audience | Document | Purpose |
|----------|----------|---------|
| **Developers** | [Setup](SETUP.md) | Environment setup, dependencies, local dev |
| | [Architecture](ARCHITECTURE.md) | Tech stack, provider routing, caching strategy |
| | [API Reference](API_REFERENCE.md) | All endpoints, request/response schemas |
| | [Testing](TESTING.md) | Test stack, fixtures, running tests |
| **QA Engineers** | [QA Guide](QA_ENGINEER.md) | Test plans, acceptance criteria, verification |
| **Project Managers** | [PM Overview](PROJECT_MANAGER.md) | Scope, dependencies, delivery tracking |
| **End Users** | [End User Guide](END_USER.md) | How the gateway powers AI features |

## Key Features

- **Unified API**: Single `/api/v1/generate` endpoint for all services
- **Provider Routing**: Admin-configurable per-customer AI model overrides
- **Response Caching**: Redis-backed cache reduces duplicate API calls
- **Rate Limiting**: Per-provider RPM limits prevent quota exhaustion
- **Cost Tracking**: Every request logged with token counts and USD cost
- **Service Auth**: X-Service-Key header prevents unauthorized access

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
