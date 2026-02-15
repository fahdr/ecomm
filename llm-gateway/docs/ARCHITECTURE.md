# LLM Gateway Architecture

> Part of [LLM Gateway](README.md) documentation

Technical architecture, design decisions, and implementation patterns.

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Framework** | FastAPI 0.110+ |
| **Language** | Python 3.11+ |
| **Database** | PostgreSQL 14+ (async via asyncpg) |
| **ORM** | SQLAlchemy 2.0 (async) |
| **Cache** | Redis 6.2+ (redis.asyncio) |
| **Testing** | pytest, httpx, pytest-asyncio |
| **Validation** | Pydantic 2.0 |

## Project Structure

```
llm-gateway/backend/
├── app/
│   ├── api/              # generate, providers, overrides, usage, health
│   ├── models/           # provider_config, customer_override, usage_log
│   ├── services/         # router_service, cache_service, cost_service, rate_limit_service
│   ├── providers/        # base, claude, openai_provider, gemini, llama, mistral, custom
│   ├── main.py           # FastAPI entry point
│   ├── config.py         # pydantic-settings config
│   └── database.py       # Session factory
└── tests/                # 42 tests with schema isolation
```

## Request Flow

```
Client (service) -> POST /api/v1/generate + X-Service-Key
  -> Authentication (401 if invalid)
  -> Router Service: resolve provider & model (check overrides, then default)
  -> Cache Service: check Redis (cache hit -> return + log)
  -> Rate Limit Service: check RPM (429 if exceeded)
  -> Provider: call AI API (502 if fails)
  -> Cost Service: calculate USD cost
  -> Usage Log: persist to DB
  -> Cache Service: store in Redis
  -> Return GenerateResponse
```

## Provider Routing Logic

Priority order for selecting provider and model:

1. **Customer + Service Override:** `user_id` + `service_name` match
2. **Customer-Wide Override:** `user_id` match + `service_name` IS NULL
3. **Global Default:** `LLM_GATEWAY_DEFAULT_PROVIDER` and `LLM_GATEWAY_DEFAULT_MODEL`

## Caching Strategy

**Key generation:** SHA-256 hash of `{provider, model, prompt, system, temperature, json_mode}`. Redis key: `llm_cache:<digest>`.

| Setting | Value |
|---------|-------|
| TTL | 3600s (configurable via `CACHE_TTL_SECONDS`) |
| Invalidation | Automatic expiry only |
| Scope | Cross-service (identical prompts share cache) |
| Disable | Set `CACHE_TTL_SECONDS=0` |

Cache hits tracked in usage logs (`cached=True/False`). Hit rate visible via `/api/v1/usage/summary`.

## Rate Limiting

Uses a sliding window counter in Redis per provider:

- Redis key: `llm_rate:<provider_name>`, value = request count, TTL = 60 seconds
- Configured per provider: `rate_limit_rpm` (default: 60), `rate_limit_tpm` (default: 100,000, not yet enforced)
- Returns `429 Too Many Requests` when exceeded

## Cost Tracking

Pricing hardcoded in `cost_service.py` as `(provider, model_prefix) -> (input_cost_per_1M, output_cost_per_1M)`.

Formula: `cost_usd = (input_tokens * input_cost + output_tokens * output_cost) / 1_000_000`

Every request creates a `UsageLog` entry with user_id, service, provider, model, tokens, cost, latency, cached status, and error (if any).

## Service Authentication

All endpoints except `/health` require `X-Service-Key` header, configured via `LLM_GATEWAY_SERVICE_KEY` env var. All 8 services share the same key. Future consideration: JWT with per-service keys.

## Database Schema

### llm_provider_configs

Stores AI provider configurations: `id` (UUID PK), `name` (unique), `display_name`, `api_key_encrypted`, `base_url`, `models` (JSON), `is_enabled`, `rate_limit_rpm`, `rate_limit_tpm`, `priority`, `extra_config` (JSON), timestamps.

### llm_customer_overrides

Per-customer routing overrides: `id` (UUID PK), `user_id`, `service_name` (nullable = all services), `provider_name`, `model_name`, timestamps. Indexed on `(user_id, service_name)`.

### llm_usage_logs

Append-only request log: `id` (UUID PK), `user_id`, `service_name`, `task_type`, `provider_name`, `model_name`, `input_tokens`, `output_tokens`, `cost_usd`, `latency_ms`, `cached`, `error`, `prompt_preview`, `created_at`. Indexed on `user_id`, `service_name`, `provider_name`, `created_at`.

## Design Decisions

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| Shared PostgreSQL database | Simplifies deployment; `llm_` prefix prevents collisions | Schema migrations must coordinate |
| Redis DB 3 for cache + rate limits | Atomic ops, auto TTL, fast lookups | Requires Redis for rate limiting |
| httpx async provider clients | Non-blocking for FastAPI, enables parallel requests | -- |
| No streaming support | Simpler implementation; caching requires full response; most use cases don't need it | Future: add `/generate-stream` for chat |

---

*See also: [Setup](SETUP.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
