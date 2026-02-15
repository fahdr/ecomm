# LLM Gateway API Reference

> Part of [LLM Gateway](README.md) documentation

Complete API endpoint documentation with request/response schemas.

**Base URL:** `http://localhost:8200/api/v1`

**Authentication:** All endpoints except `/health` require `X-Service-Key: dev-gateway-key` header.

## Health

### GET /health

Basic service health check. Returns `{status, service, database}`.

### GET /health/providers

Check status of configured providers. Returns `{providers: [{name, display_name, is_enabled, models_count}]}`.

---

## Generation

### POST /generate

Generate an LLM completion.

**Request fields:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `user_id` | string | Yes | -- | Requesting customer's user ID |
| `service` | string | Yes | -- | Calling service name |
| `task_type` | string | No | `"general"` | Task label for analytics |
| `prompt` | string | Yes | -- | User message / prompt text |
| `system` | string | No | `""` | System instruction |
| `max_tokens` | integer | No | 1000 | Max output tokens (1-8000) |
| `temperature` | float | No | 0.7 | Sampling temperature (0.0-2.0) |
| `json_mode` | boolean | No | false | Request structured JSON output |

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `content` | string | Generated text |
| `provider` | string | Provider that handled the request |
| `model` | string | Model used |
| `input_tokens` | integer | Input token count |
| `output_tokens` | integer | Output token count |
| `cost_usd` | float | Estimated cost in USD |
| `cached` | boolean | Whether served from cache |
| `latency_ms` | integer | End-to-end latency in ms |

**Errors:** `401` invalid key, `429` rate limit, `502` provider failure, `503` no enabled provider

---

## Providers

### GET /providers

List all configured providers. Returns array of provider objects with `{id, name, display_name, base_url, models, is_enabled, rate_limit_rpm, rate_limit_tpm, priority, created_at, updated_at}`.

### POST /providers

Create a new provider configuration.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | Yes | Unique short ID |
| `display_name` | string | Yes | Human-readable name |
| `api_key` | string | Yes | Provider API key |
| `base_url` | string | No | Custom endpoint URL |
| `models` | string[] | Yes | Supported model list |
| `is_enabled` | boolean | No | Default: true |
| `rate_limit_rpm` | integer | No | Default: 60 |
| `rate_limit_tpm` | integer | No | Default: 100000 |
| `priority` | integer | No | Default: 10 (higher = preferred) |

**Success:** `201 Created`. **Error:** `409 Conflict` if name exists.

### GET /providers/{provider_id}

Fetch a single provider. **Error:** `404 Not Found`

### PATCH /providers/{provider_id}

Update a provider (all fields optional). Returns updated provider.

### DELETE /providers/{provider_id}

Delete a provider. Returns `204 No Content`. **Error:** `404 Not Found`

### POST /providers/{provider_id}/test

Test connectivity. Returns `{success: bool, error: string|null}`.

---

## Overrides

Customer-specific provider/model routing overrides.

### GET /overrides

List overrides. Optional `user_id` query parameter to filter.

Returns array of `{id, user_id, service_name, provider_name, model_name, created_at, updated_at}`. `service_name=null` means override applies to all services.

### POST /overrides

Create override. Fields: `user_id` (required), `service_name` (optional, null = all services), `provider_name` (required), `model_name` (required).

**Success:** `201 Created`

### DELETE /overrides/{override_id}

Delete override. Returns `204 No Content`. **Error:** `404 Not Found`

---

## Usage

### GET /usage/summary

Aggregated usage summary. Optional `days` parameter (1-365, default: 30).

Returns `{period_days, total_requests, total_cost_usd, total_tokens, cached_requests, error_requests, cache_hit_rate}`.

### GET /usage/by-provider

Breakdown by provider. Optional `days` parameter (default: 30).

Returns array of `{provider_name, request_count, total_cost_usd, avg_latency_ms, total_tokens}`.

### GET /usage/by-service

Breakdown by calling service. Optional `days` parameter (default: 30).

Returns array of `{service_name, request_count, total_cost_usd, total_tokens}`.

### GET /usage/by-customer

Breakdown by customer. Optional `days` (default: 30) and `limit` (1-500, default: 50) parameters.

Returns array of `{user_id, request_count, total_cost_usd}`.

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [Testing](TESTING.md)*
