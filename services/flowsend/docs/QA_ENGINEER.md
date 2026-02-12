# FlowSend -- QA Engineer Guide

## Overview

FlowSend (Smart Email Marketing) is the most feature-rich and test-heavy service in the platform. It has **87 backend tests** -- the highest count across all services -- covering contacts, flows, campaigns, templates, analytics, billing, API keys, and authentication. This guide provides everything a QA engineer needs to test the service thoroughly.

---

## Test Stack

| Tool | Purpose |
|------|---------|
| **pytest** | Test runner |
| **pytest-asyncio** | Async test support |
| **httpx.AsyncClient** | HTTP client for API testing |
| **SQLAlchemy 2.0 (async)** | Database access in fixtures |
| **PostgreSQL 16** | Test database (same instance, TRUNCATE between tests) |

---

## Running Tests

```bash
# Run all 87 tests
make test-backend

# Verbose output with test names
pytest -v

# Run a specific test file
pytest tests/test_contacts.py -v

# Run a single test by name
pytest tests/test_flows.py -v -k "test_activate_flow_with_steps"

# Run with output (useful for debugging)
pytest -v -s
```

**Note:** FlowSend has **87 tests** -- the highest count of all services. All tests run in Stripe mock mode (no real API calls).

---

## Test Coverage Table

| Test File | Test Count | Scope |
|-----------|-----------|-------|
| `test_contacts.py` | 22 | Contact CRUD, bulk import (email + CSV), deduplication, contact lists, pagination, search, tag filter, count, auth |
| `test_flows.py` | 24 | Flow CRUD, lifecycle (draft/active/paused), activate with/without steps, pause active/draft, update active rejected, update paused, reactivate, executions, auth |
| `test_campaigns.py` | 21 | Campaign CRUD, scheduling, mock send, send-already-sent rejected, delete-sent rejected, analytics, events, status filter, auth |
| `test_templates.py` | 18 | Template CRUD, minimal create, validation (missing fields, empty name), category filter, pagination, partial update, auth |
| `test_auth.py` | 11 | Register (success, duplicate, short password), login (success, wrong password, nonexistent), refresh (success, access-token-fails), profile, unauthenticated |
| `test_billing.py` | 9 | List plans (public), plan pricing, checkout pro, checkout free fails, duplicate subscription fails, billing overview, overview after subscribe, current subscription (none, after subscribe) |
| `test_api_keys.py` | 5 | Create key (raw key returned), list keys (no raw keys), revoke key, auth via API key, invalid API key |
| `test_health.py` | 1 | Health check returns 200 with service metadata |
| **Total** | **87** | |

---

## Test Structure

### Fixtures (from `conftest.py`)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `event_loop` | session | Single event loop for all tests |
| `setup_db` | function (autouse) | Creates tables before tests, terminates non-self connections and TRUNCATE CASCADE after each test |
| `db` | function | Raw `AsyncSession` for direct database access |
| `client` | function | Unauthenticated `httpx.AsyncClient` pointing to `http://test` |
| `auth_headers` | function | Dict with `Authorization: Bearer <token>` for a freshly registered user |

### Helper Functions

| Function | Description |
|----------|-------------|
| `register_and_login(client, email?)` | Registers a user and returns auth headers dict |
| `_create_contact(client, headers, email)` | Creates a contact and returns its UUID (used in campaign tests) |

### Test Isolation

- Every test gets a clean database state via `TRUNCATE TABLE ... CASCADE` on all tables.
- Before truncation, all non-self database connections are terminated to prevent deadlocks.
- The `NullPool` connection pool is used in tests for isolation.

---

## API Documentation

### Interactive Docs

- **Swagger UI**: http://localhost:8104/docs
- **ReDoc**: http://localhost:8104/redoc

### Base URL

All API endpoints are prefixed with `/api/v1/`.

---

## Endpoint Summary

### Auth Endpoints

| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| POST | `/auth/register` | 201 | Register new user, returns JWT tokens |
| POST | `/auth/login` | 200 | Login with email/password, returns JWT tokens |
| POST | `/auth/refresh` | 200 | Refresh expired access token |
| GET | `/auth/me` | 200 | Get authenticated user profile |
| POST | `/auth/forgot-password` | 200 | Request password reset (always returns success) |
| POST | `/auth/provision` | 201 | Cross-service user provisioning (API key auth) |

### Contact Endpoints

| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| POST | `/contacts` | 201 | Create contact (enforces plan limits, rejects duplicates) |
| GET | `/contacts` | 200 | List contacts with pagination, search, tag filter |
| GET | `/contacts/count` | 200 | Total contact count for KPI display |
| GET | `/contacts/{id}` | 200 | Get single contact by UUID |
| PATCH | `/contacts/{id}` | 200 | Update contact fields (partial) |
| DELETE | `/contacts/{id}` | 204 | Delete contact |
| POST | `/contacts/import` | 200 | Bulk import from email list or CSV |
| POST | `/contacts/lists` | 201 | Create contact list (static or dynamic) |
| GET | `/contacts/lists` | 200 | List contact lists with pagination |
| DELETE | `/contacts/lists/{id}` | 204 | Delete contact list |

### Flow Endpoints

| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| POST | `/flows` | 201 | Create flow (starts as draft) |
| GET | `/flows` | 200 | List flows with pagination and status filter |
| GET | `/flows/{id}` | 200 | Get single flow by UUID |
| PATCH | `/flows/{id}` | 200 | Update flow (draft or paused only, 400 if active) |
| DELETE | `/flows/{id}` | 204 | Delete flow and all executions |
| POST | `/flows/{id}/activate` | 200 | Activate flow (requires at least one step, 400 if empty) |
| POST | `/flows/{id}/pause` | 200 | Pause active flow (400 if not active) |
| GET | `/flows/{id}/executions` | 200 | List flow executions with pagination |

### Campaign Endpoints

| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| POST | `/campaigns` | 201 | Create campaign (draft or scheduled) |
| GET | `/campaigns` | 200 | List campaigns with pagination and status filter |
| GET | `/campaigns/{id}` | 200 | Get single campaign by UUID |
| PATCH | `/campaigns/{id}` | 200 | Update campaign (draft/scheduled only, 400 if sent) |
| DELETE | `/campaigns/{id}` | 204 | Delete campaign (draft only, 400 if sent) |
| POST | `/campaigns/{id}/send` | 200 | Send campaign (mock: creates email events for all subscribed contacts) |
| GET | `/campaigns/{id}/analytics` | 200 | Per-campaign analytics (sent, opened, clicked, bounced, rates) |
| GET | `/campaigns/{id}/events` | 200 | List email events for campaign with pagination and type filter |

### Template Endpoints

| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| POST | `/templates` | 201 | Create custom template (name, subject, html_content required) |
| GET | `/templates` | 200 | List templates (custom + system) with category filter |
| GET | `/templates/{id}` | 200 | Get single template (own or system) |
| PATCH | `/templates/{id}` | 200 | Update custom template (400 for system templates) |
| DELETE | `/templates/{id}` | 204 | Delete custom template (400 for system templates) |

### Analytics Endpoints

| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| GET | `/analytics` | 200 | Aggregate analytics (totals, rates, per-campaign breakdown) |

### Billing Endpoints

| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| GET | `/billing/plans` | 200 | List all plans (public, no auth required) |
| POST | `/billing/checkout` | 201 | Create Stripe checkout session (400 for free plan or duplicate) |
| POST | `/billing/portal` | 200 | Create Stripe customer portal session |
| GET | `/billing/current` | 200 | Get current subscription (null if none) |
| GET | `/billing/overview` | 200 | Full billing overview (plan, subscription, usage metrics) |

### API Key Endpoints

| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| POST | `/api-keys` | 201 | Create API key (raw key returned ONCE) |
| GET | `/api-keys` | 200 | List API keys (no raw keys, prefix only) |
| DELETE | `/api-keys/{id}` | 204 | Revoke (deactivate) API key |

### Other Endpoints

| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| GET | `/usage` | 200 | Usage metrics (JWT or API key auth) |
| POST | `/webhooks/stripe` | 200 | Stripe webhook handler |
| GET | `/health` | 200 | Health check |

---

## CAN-SPAM Compliance Testing

FlowSend includes CAN-SPAM compliance features that must be verified:

1. **Unsubscribe handling**: When a contact's `is_subscribed` is set to `false`, the `unsubscribed_at` timestamp is automatically recorded.
2. **Unsubscribe records table**: A dedicated `unsubscribes` table tracks all unsubscribe events.
3. **Contact subscription status**: Every contact has `is_subscribed` (boolean) and `unsubscribed_at` (datetime) fields.
4. **Campaign send filtering**: The mock send function (`send_campaign_mock`) only creates `EmailEvent` records for subscribed contacts (`is_subscribed=True`).
5. **Import deduplication**: Bulk import respects existing contacts and does not re-subscribe unsubscribed contacts.

### CAN-SPAM Test Scenarios

- Create a contact, unsubscribe them via PATCH (`is_subscribed: false`), verify `unsubscribed_at` is set.
- Send a campaign with both subscribed and unsubscribed contacts, verify only subscribed contacts receive email events.
- Import contacts that already exist -- verify they are skipped, not re-subscribed.

---

## Verification Checklist

### Authentication
- [ ] Registration returns 201 with access + refresh tokens
- [ ] Duplicate email registration returns 409
- [ ] Short password (<8 chars) returns 422
- [ ] Login with valid credentials returns 200 with tokens
- [ ] Login with wrong password returns 401
- [ ] Login with nonexistent email returns 401
- [ ] Token refresh with valid refresh token returns new tokens
- [ ] Token refresh with access token returns 401
- [ ] GET /auth/me returns user profile with plan and active status
- [ ] All protected endpoints return 401 without token

### Contacts
- [ ] Create contact with full payload returns 201
- [ ] Create contact with only email (minimal) returns 201
- [ ] Create contact with invalid email returns 422
- [ ] Create duplicate email returns 400
- [ ] List contacts with pagination works correctly
- [ ] Search by email substring filters correctly
- [ ] Tag filter returns only matching contacts
- [ ] Get contact by UUID returns correct data
- [ ] Get contact with unknown UUID returns 404
- [ ] Update contact partially (only provided fields change)
- [ ] Unsubscribe via PATCH (`is_subscribed: false`) works
- [ ] Delete contact returns 204, subsequent GET returns 404
- [ ] Import email list creates correct number of contacts
- [ ] Import with duplicates reports correct skipped count
- [ ] Import CSV with first_name/last_name columns works
- [ ] Contact count endpoint reflects actual count
- [ ] Contact lists: create static, create dynamic (with rules), list, delete

### Flows
- [ ] Create flow in draft status with all fields
- [ ] Create flow with only required fields (name, trigger_type)
- [ ] All trigger types accepted: signup, purchase, abandoned_cart, custom, scheduled
- [ ] Missing name returns 422
- [ ] Missing trigger_type returns 422
- [ ] List flows with pagination works
- [ ] Status filter (draft, active, paused) works
- [ ] Get flow by UUID returns correct data
- [ ] Update draft flow changes only provided fields
- [ ] Delete flow returns 204
- [ ] Activate flow with steps transitions to "active"
- [ ] Activate flow without steps returns 400
- [ ] Pause active flow transitions to "paused"
- [ ] Pause draft flow returns 400
- [ ] Update active flow returns 400 (must pause first)
- [ ] Update paused flow succeeds
- [ ] Reactivate paused flow transitions back to "active"
- [ ] List flow executions returns paginated results

### Campaigns
- [ ] Create draft campaign (no scheduled_at)
- [ ] Create scheduled campaign (with scheduled_at)
- [ ] Missing name or subject returns 422
- [ ] List campaigns with pagination works
- [ ] Status filter (draft, scheduled, sent) works
- [ ] Get campaign by UUID returns correct data
- [ ] Update draft campaign changes fields
- [ ] Delete draft campaign returns 204
- [ ] Send campaign transitions to "sent" with sent_at timestamp
- [ ] Send already-sent campaign returns 400
- [ ] Delete sent campaign returns 400
- [ ] Campaign analytics returns totals and rates
- [ ] Campaign events returns paginated email events

### Templates
- [ ] Create template with all fields returns 201 with is_system=false
- [ ] Create minimal template uses default category "newsletter"
- [ ] Missing required fields (name, subject, html_content) returns 422
- [ ] Empty name returns 422
- [ ] List templates includes custom and system templates
- [ ] Category filter works correctly
- [ ] Update custom template changes only provided fields
- [ ] Delete custom template returns 204
- [ ] System templates cannot be updated (400)
- [ ] System templates cannot be deleted (400)

### Billing
- [ ] List plans returns all 3 tiers (free, pro, enterprise) -- public endpoint
- [ ] Plan pricing is correct (0, 3900, 14900 cents)
- [ ] Checkout for pro plan returns 201 with checkout URL
- [ ] Checkout for free plan returns 400
- [ ] Duplicate subscription checkout returns 400
- [ ] Billing overview shows correct plan and usage metrics
- [ ] Overview reflects plan change after checkout
- [ ] Current subscription is null for free users
- [ ] Current subscription shows plan and status after checkout

### API Keys
- [ ] Create key returns 201 with raw key (shown once)
- [ ] List keys returns metadata without raw keys
- [ ] Revoke key marks it as inactive (is_active=false)
- [ ] Auth via X-API-Key header works for usage endpoint
- [ ] Invalid API key returns 401

---

## Feature Verification

### Dashboard Pages (9 pages)

| Page | Route | Key Elements to Verify |
|------|-------|----------------------|
| Dashboard Home | `/` | KPI cards (plan, API calls, API keys), quick action buttons, loading skeletons |
| Contacts | `/contacts` | Contact table, search, import dialog, create/edit/delete dialogs, pagination |
| Flows | `/flows` | Flow list with status icons, status filter tabs, create/edit/activate/pause/delete dialogs |
| Campaigns | `/campaigns` | Campaign list, status filter, create/edit/send/delete dialogs, analytics dialog |
| Templates | `/templates` | (verify navigation route exists) |
| Analytics | `/analytics` | (verify navigation route exists) |
| API Keys | `/api-keys` | Key list, create dialog, revoke confirmation |
| Billing | `/billing` | Plan cards, checkout flow, current subscription display |
| Settings | `/settings` | Account settings |
| Login | `/login` | Email/password form, error handling |
| Register | `/register` | Email/password form, validation |

### Cross-Browser Verification

- Verify all dashboard pages render correctly in Chrome, Firefox, and Safari.
- Verify responsive layout collapses grid on mobile viewports.
- Verify OKLCH colors render with hex fallbacks in older browsers.
- Verify Satoshi and Inter fonts load correctly.
