# API Reference

> Part of [Admin Dashboard](README.md) documentation

Complete reference for all Super Admin Dashboard backend endpoints.

**Base URL:** `http://localhost:8300/api/v1/admin`

**Authentication:** All endpoints except `/auth/setup` and `/auth/login` require `Authorization: Bearer <token>`.

## Authentication

### POST /auth/setup

Create the first super_admin account (one-time operation).

| Field | Type | Required |
|-------|------|----------|
| `email` | string | Yes |
| `password` | string | Yes |

**Success:** `201 Created` -- returns `{id, email, role, is_active}`

**Error:** `409 Conflict` if admin already exists

### POST /auth/login

Authenticate and receive a JWT token.

| Field | Type | Required |
|-------|------|----------|
| `email` | string | Yes |
| `password` | string | Yes |

**Success:** `200 OK` -- returns `{access_token, token_type}`

**Errors:** `401 Unauthorized` (invalid credentials or deactivated account)

### GET /auth/me

Get the currently authenticated admin's profile.

**Success:** `200 OK` -- returns `{id, email, role, is_active}`

**Error:** `401 Unauthorized` (missing, invalid, or expired token)

---

## Health Monitoring

### GET /health/services

Ping all managed services and return their current health status.

**Response:** `200 OK` with `{checked_at, services: [...]}`

Each service entry: `{service_name, status, response_time_ms, checked_at}`

**Status values:**
- `healthy` -- responded with HTTP 200 and `{"status": "healthy"}`
- `degraded` -- responded but non-healthy status or non-200 code
- `down` -- timed out, connection error, or exception

Notes: Pings all services concurrently with 5-second timeout. Persists a health snapshot per service.

### GET /health/history

Get historical health check snapshots.

| Parameter | Default | Notes |
|-----------|---------|-------|
| `limit` | 50 | Max 500 |
| `service_name` | (all) | Filter by service |

**Response:** `200 OK` -- array of `{id, service_name, status, response_time_ms, checked_at}`, ordered by `checked_at` descending.

---

## LLM Providers

All provider endpoints are proxied to the LLM Gateway.

### GET /llm/providers

List all configured LLM providers.

**Response:** `200 OK` -- array of provider objects with `{id, name, display_name, base_url, models, is_enabled, rate_limit_rpm, rate_limit_tpm, priority, created_at, updated_at}`

### POST /llm/providers

Create a new LLM provider.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | Yes | Short ID (e.g., `openai`) |
| `display_name` | string | Yes | Human-readable name |
| `api_key` | string | Yes | Provider API key |
| `base_url` | string | No | Custom endpoint |
| `models` | string[] | Yes | Supported models |
| `is_enabled` | boolean | No | Default: true |
| `rate_limit_rpm` | integer | No | Requests per minute |
| `rate_limit_tpm` | integer | No | Tokens per minute |
| `priority` | integer | No | Routing priority (higher = preferred) |

**Success:** `201 Created` -- returns provider object

### PATCH /llm/providers/:id

Update an existing LLM provider (partial update).

**Success:** `200 OK` -- returns updated provider object

### DELETE /llm/providers/:id

Delete an LLM provider.

**Success:** `204 No Content`

---

## LLM Usage Analytics

All usage endpoints are proxied to the LLM Gateway.

### GET /llm/usage/summary

Aggregated LLM usage summary. Optional `days` parameter (default: 30).

**Response:** `200 OK` -- `{period_days, total_requests, total_cost_usd, total_tokens, cached_requests, error_requests, cache_hit_rate}`

### GET /llm/usage/by-provider

Usage breakdown by provider. Optional `days` parameter (default: 30).

**Response:** `200 OK` -- array of `{provider_name, request_count, total_cost_usd, avg_latency_ms, total_tokens}`

### GET /llm/usage/by-service

Usage breakdown by calling service. Optional `days` parameter (default: 30).

**Response:** `200 OK` -- array of `{service_name, request_count, total_cost_usd, total_tokens}`

---

## Service Overview

### GET /services

List all managed services with their last known health status.

**Response:** `200 OK` -- array of `{name, port, url, last_status, last_response_time_ms, last_checked_at}`

**Status values:** `healthy`, `degraded`, `down`, `unknown` (no checks recorded yet)

---

## Error Responses

| Code | Meaning | Example detail |
|------|---------|----------------|
| `401` | Unauthorized | `"Invalid token"` |
| `403` | Forbidden | `"Insufficient permissions"` |
| `404` | Not Found | `"Resource not found"` |
| `502` | Bad Gateway | `"Cannot connect to LLM Gateway"` |
| `504` | Gateway Timeout | `"LLM Gateway request timed out"` |

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [Testing](TESTING.md) · [End User Guide](END_USER.md)*
