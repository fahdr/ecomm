# QA Engineer Guide — Dropshipping Platform

## Test Suite Overview

- **Location:** `dropshipping/backend/tests/`
- **Total tests:** 580
- **Framework:** pytest + pytest-asyncio + httpx AsyncClient

### Running Tests

```bash
cd dropshipping/backend
python -m pytest tests/ -v
```

### Test Isolation

All tests use schema-based isolation (`dropshipping_test` PostgreSQL schema).
This prevents cross-contamination with other services sharing the same database.

---

## ServiceBridge Tests (39 tests)

### test_bridge_tasks.py (16 tests)
- Event-to-service mapping verification for all 5 event types
- Successful delivery recording
- HTTP error handling and timeout handling
- HMAC signature correctness
- Mixed results (some succeed, some fail)
- Missing base URL handling

### test_bridge_service.py (10 tests)
- HMAC signing determinism and secret variation
- `fire_platform_event` correct Celery `.delay()` arguments
- Empty result queries (activity, resource, service, summary)

### test_bridge_api.py (13 tests)
- Auth required (401) on all 5 endpoints
- Empty paginated response for new users
- Pagination and filter parameter handling
- Manual dispatch fires event and returns confirmation
- Missing fields return 422 validation error

---

## E2E Tests (Playwright)

### service-bridge.spec.ts (15 tests)

| Test Group | Tests | Coverage |
|-----------|-------|---------|
| Bridge API Endpoints | 7 | Activity, summary, resource, dispatch, auth, validation |
| Service Activity Page | 4 | Empty state, KPI cards, filters, back navigation |
| Services Hub | 2 | All 8 service cards, enable buttons |
| Product Detail Panel | 2 | Connected services panel, 8-service grid |
| Sidebar Navigation | 2 | Activity link visible, navigation works |

---

## Acceptance Criteria — ServiceBridge

1. Creating a product fires `product.created` to 6 connected services
2. Updating a product fires `product.updated` to 3 services
3. Order fulfillment fires `order.shipped` to FlowSend
4. Customer registration fires `customer.created` to FlowSend
5. Each delivery is recorded with status, latency, error details
6. Dashboard activity page shows paginated delivery history
7. Filters (event, service, status) work correctly
8. Product/order detail pages show per-resource service status
9. Services hub shows health indicators per service
10. Manual dispatch endpoint fires event and returns confirmation

---

## Edge Cases

- No connected services: event fires but nothing is delivered
- Service returns non-200: delivery recorded as failed with error
- Service times out: delivery recorded with timeout error
- Missing `platform_webhook_secret`: uses default dev secret
- Null `store_id`: supported for customer events (public endpoint)
