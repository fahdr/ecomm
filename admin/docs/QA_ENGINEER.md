# QA Engineer Guide

> Part of [Admin Dashboard](README.md) documentation

Quality assurance criteria, test scenarios, and verification checklists for the Super Admin Dashboard.

## Overview

The Super Admin Dashboard is a **critical infrastructure service** that monitors the entire ecomm platform. Any failures here can blind operators to issues in production. QA must ensure:

- Service health monitoring is accurate and timely
- LLM cost data is correct (financial reporting)
- Admin authentication is secure (protects platform access)
- Proxied endpoints correctly forward to the LLM Gateway

## Acceptance Criteria

### Authentication (AC-AUTH)

**AC-AUTH-1:** First-time setup creates a super_admin account
- **Given:** No admin users exist in the database
- **When:** POST /auth/setup with email and password
- **Then:** Response is 201 with role="super_admin"

**AC-AUTH-2:** Setup fails when admin already exists
- **Given:** An admin user exists
- **When:** POST /auth/setup
- **Then:** Response is 409 with "Admin user already exists" message

**AC-AUTH-3:** Login returns a valid JWT token
- **Given:** A super_admin account exists
- **When:** POST /auth/login with correct email/password
- **Then:** Response is 200 with a JWT token that validates

**AC-AUTH-4:** Login fails with wrong credentials
- **Given:** A super_admin account exists
- **When:** POST /auth/login with wrong password
- **Then:** Response is 401 with "Invalid email or password" message

**AC-AUTH-5:** Deactivated admins cannot log in
- **Given:** An admin account with is_active=false
- **When:** POST /auth/login with correct credentials
- **Then:** Response is 401 with "Admin account is deactivated" message

**AC-AUTH-6:** Profile endpoint returns admin details
- **Given:** A valid JWT token
- **When:** GET /auth/me
- **Then:** Response is 200 with id, email, role, is_active

**AC-AUTH-7:** Expired tokens are rejected
- **Given:** A JWT token past its expiration time
- **When:** Any authenticated endpoint
- **Then:** Response is 401 with "Token has expired" message

### Health Monitoring (AC-HEALTH)

**AC-HEALTH-1:** Health check pings all configured services
- **Given:** 9 services in settings.service_urls
- **When:** GET /health/services
- **Then:** Response contains 9 service results

**AC-HEALTH-2:** Healthy services show "healthy" status
- **Given:** A service responds HTTP 200 with {"status": "healthy"}
- **When:** Health check is performed
- **Then:** Service status is "healthy" with response_time_ms

**AC-HEALTH-3:** Non-responsive services show "down" status
- **Given:** A service is not running or times out
- **When:** Health check is performed
- **Then:** Service status is "down" with response_time_ms=null

**AC-HEALTH-4:** Health snapshots are persisted
- **Given:** Health check is performed
- **When:** Snapshots are created
- **Then:** Database contains ServiceHealthSnapshot rows for all services

**AC-HEALTH-5:** Health history returns latest snapshots
- **Given:** Multiple health snapshots exist
- **When:** GET /health/history
- **Then:** Response is ordered by checked_at descending

**AC-HEALTH-6:** Health history respects service filter
- **Given:** Snapshots for multiple services
- **When:** GET /health/history?service_name=llm-gateway
- **Then:** Response contains only llm-gateway snapshots

**AC-HEALTH-7:** Health history respects limit parameter
- **Given:** 100 snapshots exist
- **When:** GET /health/history?limit=10
- **Then:** Response contains exactly 10 snapshots

### LLM Providers (AC-PROVIDER)

**AC-PROVIDER-1:** List providers proxies to gateway
- **Given:** Gateway has 2 providers configured
- **When:** GET /llm/providers
- **Then:** Response contains 2 provider dicts

**AC-PROVIDER-2:** Create provider forwards request
- **Given:** Valid provider data
- **When:** POST /llm/providers
- **Then:** Response is 201 with created provider

**AC-PROVIDER-3:** Update provider forwards partial data
- **Given:** An existing provider
- **When:** PATCH /llm/providers/:id with {display_name: "New Name"}
- **Then:** Response is 200 with updated display_name

**AC-PROVIDER-4:** Delete provider forwards request
- **Given:** An existing provider
- **When:** DELETE /llm/providers/:id
- **Then:** Response is 204 No Content

**AC-PROVIDER-5:** Proxy includes service key header
- **Given:** Any provider endpoint
- **When:** Request is proxied to gateway
- **Then:** X-Service-Key header is set to LLM_GATEWAY_KEY

**AC-PROVIDER-6:** Proxy handles gateway errors
- **Given:** Gateway returns 500
- **When:** Provider endpoint is called
- **Then:** Response is 500 with gateway error message

**AC-PROVIDER-7:** Proxy handles gateway timeout
- **Given:** Gateway does not respond within 10s
- **When:** Provider endpoint is called
- **Then:** Response is 504 with "LLM Gateway request timed out" message

### LLM Usage Analytics (AC-USAGE)

**AC-USAGE-1:** Usage summary returns aggregate data
- **Given:** Gateway has usage logs
- **When:** GET /llm/usage/summary
- **Then:** Response contains total_requests, total_cost_usd, cache_hit_rate

**AC-USAGE-2:** By-provider breakdown sums per provider
- **Given:** Usage logs for multiple providers
- **When:** GET /llm/usage/by-provider
- **Then:** Response groups by provider_name with cost totals

**AC-USAGE-3:** By-service breakdown sums per service
- **Given:** Usage logs from multiple services
- **When:** GET /llm/usage/by-service
- **Then:** Response groups by service_name with cost totals

**AC-USAGE-4:** Days parameter filters usage period
- **Given:** Usage logs spanning 60 days
- **When:** GET /llm/usage/summary?days=30
- **Then:** Response period_days=30 and data covers last 30 days

**AC-USAGE-5:** Cost values are accurate to 4 decimal places
- **Given:** Usage logs with fractional costs
- **When:** Usage endpoints are called
- **Then:** total_cost_usd values have 4 decimal precision

### Service Overview (AC-SERVICE)

**AC-SERVICE-1:** Service list returns all 9 services
- **Given:** settings.service_urls has 9 entries
- **When:** GET /services
- **Then:** Response contains 9 service dicts

**AC-SERVICE-2:** Services with no snapshots show "unknown"
- **Given:** A service with no health snapshots
- **When:** GET /services
- **Then:** Service last_status is "unknown"

**AC-SERVICE-3:** Services show latest snapshot status
- **Given:** A service with multiple snapshots
- **When:** GET /services
- **Then:** Service last_status matches most recent snapshot

**AC-SERVICE-4:** Port extraction works for all URLs
- **Given:** Service URLs with different formats
- **When:** Service list is generated
- **Then:** Port numbers are correctly extracted

## Verification Checklist

### Pre-Release Testing

**Backend:**
- [ ] All 34 backend tests pass with `pytest`
- [ ] No SQL injection vulnerabilities (parameterized queries only)
- [ ] No hardcoded credentials in source code
- [ ] JWT secret is not the default in production
- [ ] Database migrations run cleanly on fresh database

**Dashboard:**
- [ ] All pages load without console errors
- [ ] Status badges show correct colors (green/amber/red/gray)
- [ ] Number formatting is correct (currency, commas, percentages)
- [ ] Login redirects to overview page on success
- [ ] Logout clears token and redirects to login
- [ ] All forms validate inputs before submission

**Integration:**
- [ ] Dashboard can authenticate with backend
- [ ] Health checks actually ping configured services
- [ ] Provider CRUD operations persist to gateway database
- [ ] Cost data matches LLM Gateway's usage logs

### Security Testing

- [ ] Setup endpoint only works once (409 after first admin)
- [ ] Login requires correct password (401 for wrong password)
- [ ] Deactivated admins cannot log in (401)
- [ ] JWT tokens expire after configured time (default 480 minutes)
- [ ] Invalid JWT tokens are rejected (401)
- [ ] Missing Authorization header returns 401
- [ ] CORS allows dashboard origin (port 3300)
- [ ] Passwords are bcrypt-hashed in database (never plaintext)

### Functional Testing

**Health Monitoring:**
- [ ] "Healthy" badge appears for running services
- [ ] "Down" badge appears for stopped services
- [ ] "Degraded" badge appears for slow services
- [ ] Health history shows timestamps in local timezone
- [ ] Health snapshots persist to database
- [ ] Manual refresh button re-fetches health data

**Provider Management:**
- [ ] Add provider dialog opens on "Add Provider" click
- [ ] Provider form validates required fields
- [ ] Create provider persists to gateway
- [ ] Edit provider pre-fills form with existing values
- [ ] Delete provider shows confirmation prompt
- [ ] Provider list refreshes after mutations

**Cost Analytics:**
- [ ] Summary cards show correct totals
- [ ] By-provider table sums match summary
- [ ] By-service table sums match summary
- [ ] Percentage shares add up to ~100%
- [ ] Currency values format with 2-4 decimal places

**Service Overview:**
- [ ] All 9 services appear in grid
- [ ] Port numbers are correct
- [ ] Status badges reflect latest health check
- [ ] Refresh button updates service status
- [ ] Health summary bar shows counts (healthy/degraded/down)

### Performance Testing

- [ ] Health check completes in under 10 seconds (9 services × 5s timeout)
- [ ] Dashboard pages load in under 2 seconds
- [ ] Provider list handles 10+ providers without lag
- [ ] Usage analytics loads in under 3 seconds
- [ ] No memory leaks on repeated health checks

### Edge Cases

- [ ] Health check with all services down (all "down" status)
- [ ] Health check with no prior snapshots (all "unknown")
- [ ] Usage analytics with zero requests (displays zeros)
- [ ] Provider list with zero providers (shows empty state)
- [ ] Login with non-existent email (401 error)
- [ ] Very long provider names (UI truncates correctly)
- [ ] Very large cost values (number formatting works)

## Bug Reporting

When reporting issues, include:

**Environment:**
- Admin backend version or commit hash
- Admin dashboard version or commit hash
- PostgreSQL version
- Redis version
- Browser (for dashboard issues)

**Steps to Reproduce:**
1. Preconditions (e.g., "Given 1 admin user exists")
2. Action (e.g., "POST /auth/setup with valid data")
3. Expected result (e.g., "Should return 409")
4. Actual result (e.g., "Returns 500 with database error")

**Logs:**
- Backend logs (uvicorn output)
- Browser console errors (for dashboard issues)
- PostgreSQL error logs (for database issues)

**Test Data:**
- Request body (redact passwords/keys)
- Response body
- JWT token (redact for security, just indicate "valid" or "invalid")

---
*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [Testing](TESTING.md) · [Project Manager Guide](PROJECT_MANAGER.md)*
