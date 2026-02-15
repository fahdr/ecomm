# LLM Gateway - QA Engineer Guide

> Part of [LLM Gateway](README.md) documentation

Test plans, acceptance criteria, and verification procedures for the LLM Gateway.

## Acceptance Criteria

### Core Generation Flow

| ID | Criteria | Expected |
|----|----------|----------|
| AC-001 | Valid provider configured, valid service key, generation request sent | `200 OK` with `content`, `provider`, `model`, `cost_usd`, `cached=false` |
| AC-002 | Request sent without `X-Service-Key` header | `401 Unauthorized` |

### Caching Behavior

| ID | Criteria | Expected |
|----|----------|----------|
| AC-003 | First generation request for a given prompt | `cached=false` |
| AC-004 | Identical request sent again (same prompt, system, temperature, provider, model) | `cached=true`, latency < 100ms |
| AC-005 | Same prompt sent with different temperature | `cached=false` (new cache key) |

### Rate Limiting

| ID | Criteria | Expected |
|----|----------|----------|
| AC-006 | Provider has `rate_limit_rpm=2`, 3 requests sent within 1 minute | Third request returns `429 Too Many Requests` |
| AC-007 | Rate limit was hit, 60 seconds pass | Requests allowed again |

### Provider Routing

| ID | Criteria | Expected |
|----|----------|----------|
| AC-008 | Customer override exists for `user_id`, generation request sent | Override provider and model used |
| AC-009 | Service-specific override exists alongside customer-wide override | Service-specific override takes precedence |
| AC-010 | Customer override points to a disabled provider | `503 Service Unavailable` |

### Cost Tracking

| ID | Criteria | Expected |
|----|----------|----------|
| AC-011 | Generation request succeeds | UsageLog entry created with token counts and cost |
| AC-012 | Generation request fails (provider error) | UsageLog entry created with `error` populated, `cost_usd=0` |

### Provider Management

| ID | Criteria | Expected |
|----|----------|----------|
| AC-013 | POST to `/providers` with valid data | `201 Created` with UUID |
| AC-014 | POST to `/providers` with duplicate name | `409 Conflict` |
| AC-015 | POST to `/providers/{id}/test` | Returns `{success, error}` after connectivity test |

### Usage Analytics

| ID | Criteria | Expected |
|----|----------|----------|
| AC-016 | GET `/usage/summary?days=7` with existing logs | Returns `total_requests`, `total_cost_usd`, `cache_hit_rate` |
| AC-017 | GET `/usage/by-provider` with multiple providers | Per-provider metrics sorted by cost descending |

## Test Checklists

### Smoke Tests (5 min)

- [ ] Gateway starts and returns 200 on `/api/v1/health`
- [ ] Database and Redis connections healthy
- [ ] Can create a provider via API
- [ ] Can generate a response with valid provider

### Functional Tests (20 min)

- [ ] Generation with default provider succeeds
- [ ] Invalid service key returns 401
- [ ] Missing prompt returns 422
- [ ] Cache hit on duplicate request
- [ ] Rate limit enforced after threshold
- [ ] Customer override routes correctly
- [ ] Disabled provider returns 503
- [ ] Usage log created for every request
- [ ] Provider CRUD (create, read, update, delete)
- [ ] Override CRUD (create, list, delete)

### Edge Cases (15 min)

- [ ] Very long prompts (8000 tokens)
- [ ] Temperature edge values (0.0, 2.0)
- [ ] JSON mode enabled
- [ ] Concurrent requests (10 simultaneous)
- [ ] Provider API timeout
- [ ] Redis unavailable (graceful degradation)
- [ ] Database unavailable (502 error)

### Performance Tests (10 min)

- [ ] Cache hit latency < 100ms
- [ ] Non-cached request latency < 3s (provider-dependent)
- [ ] 100 requests/sec sustained load
- [ ] Memory usage stable under load

## Manual Testing Tips

**Reset state between tests:**
- Clear Redis cache: `redis-cli -n 3 FLUSHDB`
- Truncate usage logs: `TRUNCATE TABLE llm_usage_logs CASCADE;`

**Monitor logs:** `tail -f llm-gateway.log | grep -E "(ERROR|WARNING|generate)"`

**Check provider health:** `GET /api/v1/health/providers` with service key header

**Query usage logs:**
- Recent requests by service: `SELECT service_name, COUNT(*), SUM(cost_usd) FROM llm_usage_logs WHERE created_at > NOW() - INTERVAL '1 hour' GROUP BY service_name;`
- Cache hit rate: `SELECT COUNT(*) FILTER (WHERE cached) * 100.0 / COUNT(*) FROM llm_usage_logs WHERE created_at > NOW() - INTERVAL '1 hour';`

## Regression Test Suite

Run the full automated test suite:

```bash
cd /workspaces/ecomm/llm-gateway/backend
pytest -v --tb=short
```

Expected: **42 tests passed**, 0 failures.

---

*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [API Reference](API_REFERENCE.md) · [Testing](TESTING.md)*
