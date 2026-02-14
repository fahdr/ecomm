# Project Manager Guide

> Part of [Admin Dashboard](README.md) documentation

Project scope, dependencies, milestones, and delivery tracking for the Super Admin Dashboard.

## Executive Summary

The Super Admin Dashboard is the **centralized control plane** for the ecomm platform. It provides platform operators with:

- Real-time health monitoring for 9 platform services
- LLM provider configuration and cost analytics
- Admin user management (authentication, roles)
- Service oversight and historical uptime data

**Status:** Production-ready (Phase 3 complete)

**Key Metrics:**
- 34 backend tests (100% pass rate)
- 2 database tables
- 4 API domains (auth, health, LLM proxy, services)
- 5 dashboard pages (overview, providers, costs, services, login)

## Project Scope

### In Scope

**MVP Features (Completed):**
- [x] Admin authentication (setup, login, JWT tokens)
- [x] Service health monitoring (real-time pings, historical snapshots)
- [x] LLM Gateway proxy (provider CRUD, usage analytics)
- [x] Service overview (status badges, port numbers)
- [x] Dashboard UI (overview, providers, costs, services pages)

**Future Enhancements (Planned):**
- [ ] Role-based access control (super_admin vs. admin vs. viewer)
- [ ] Email alerts for service downtime
- [ ] Slack/webhook notifications for critical failures
- [ ] Admin user management UI (invite, deactivate, change roles)
- [ ] Health check scheduler (automated periodic pings)
- [ ] Cost budget alerts (notify when LLM spend exceeds threshold)
- [ ] Service log viewer (aggregated logs from all services)

### Out of Scope

- **Customer-facing features** — Admin dashboard is for platform operators only
- **Billing/payments** — LLM costs are tracked but not billed to customers
- **Service configuration** — Admin can view services but not change their settings
- **Direct database access** — Admin cannot run SQL queries or modify tables

## Dependencies

### Internal Dependencies

**Must be running for admin dashboard to function:**

1. **PostgreSQL 13+**
   - Stores admin users and health snapshots
   - Shared database with other platform services
   - Required tables: `admin_users`, `admin_health_snapshots`

2. **Redis 6+**
   - Database 4 for admin session cache
   - Not critical (admin can function without Redis)

3. **LLM Gateway (port 8200)**
   - Required for provider management and usage analytics
   - Without gateway, `/llm/*` endpoints return 502

**Monitored services (health checks fail if not running):**
- llm-gateway (8200)
- trendscout (8101)
- contentforge (8102)
- priceoptimizer (8103)
- reviewsentinel (8104)
- inventoryiq (8105)
- customerinsight (8106)
- adcreator (8107)
- competitorradar (8108)

### External Dependencies

None. The admin dashboard is a fully internal service.

## Architecture Decisions

**Key decisions with rationale:**

1. **Shared PostgreSQL database with table prefix**
   - Simplifies deployment (one less database)
   - `admin_` prefix prevents collisions with other services
   - Schema isolation for tests (`admin_test` schema)

2. **Proxy pattern for LLM Gateway**
   - Gateway owns its data model; admin should not access tables directly
   - Service key authentication easier to rotate than DB credentials
   - Gateway can log and audit admin operations

3. **Separate admin authentication**
   - Admin access is more sensitive than customer access
   - Independent JWT secret allows separate key rotation
   - Different expiration policy (8 hours vs. 24 hours)

4. **No Alembic migrations**
   - Schema is simple (2 tables, no foreign keys)
   - Startup creation with `create_all()` works for MVP
   - Can add Alembic later if schema complexity grows

## Milestones

### Phase 1: Core Backend (Completed)

**Delivery:** 2026-02-01

- [x] FastAPI app structure (main.py, routers, models)
- [x] Admin authentication (setup, login, JWT)
- [x] Database setup (admin_users, admin_health_snapshots)
- [x] Health monitoring API (ping services, history)
- [x] LLM Gateway proxy (providers, usage)
- [x] Service overview API

**Acceptance:**
- All endpoints documented in API reference
- 34 backend tests passing
- Setup creates first admin user

### Phase 2: Dashboard UI (Completed)

**Delivery:** 2026-02-08

- [x] Next.js dashboard scaffolding
- [x] Login page with JWT storage
- [x] Overview page (KPIs, health grid)
- [x] Providers page (CRUD dialog)
- [x] Costs page (usage tables)
- [x] Services page (status cards)

**Acceptance:**
- All pages load without errors
- Status badges show correct colors
- Provider CRUD persists to gateway

### Phase 3: Testing & Documentation (Completed)

**Delivery:** 2026-02-14

- [x] Comprehensive test suite (34 tests)
- [x] Schema isolation for test database
- [x] API reference documentation
- [x] Setup guide
- [x] Architecture documentation
- [x] QA engineer guide
- [x] Project manager guide
- [x] End user guide

**Acceptance:**
- All docs in `admin/docs/` directory
- Test coverage > 90%
- README.md with quick start

### Phase 4: Production Hardening (Future)

**Target:** TBD

- [ ] HTTPS enforcement
- [ ] Rate limiting (brute-force protection)
- [ ] Audit logging (track all admin actions)
- [ ] Email alerts for downtime
- [ ] Automated health check scheduler
- [ ] Admin user management UI

## Risks & Mitigations

### Risk 1: False "Down" Status for Healthy Services

**Risk:** Network blips cause services to appear "down" when they're actually healthy.

**Impact:** Operators waste time investigating phantom outages.

**Mitigation:**
- Increase health check timeout from 5s to 10s
- Add retry logic (2-3 attempts before marking "down")
- Show response time trend (sudden spike = network issue)

**Status:** Accepted risk for MVP; will address in Phase 4.

### Risk 2: LLM Gateway Downtime Breaks Admin

**Risk:** If gateway is down, admin cannot manage providers or view costs.

**Impact:** Operators cannot configure LLM during gateway outages.

**Mitigation:**
- Dashboard gracefully handles 502 errors (shows "Gateway Unavailable")
- Health monitoring still works (independent of gateway)
- Gateway is highly available (rarely down)

**Status:** Accepted risk; gateway SLA is 99.9%.

### Risk 3: Unauthorized Admin Access

**Risk:** JWT secret is leaked, allowing attackers to impersonate admins.

**Impact:** Attackers can view sensitive data (costs, service status) and configure providers.

**Mitigation:**
- Use strong JWT secret (256-bit random key)
- Rotate secret periodically (invalidates all tokens)
- Add IP whitelist (restrict admin access to VPN)
- Audit logging (track all admin actions)

**Status:** Mitigated with strong secret; IP whitelist in Phase 4.

### Risk 4: Slow Health Checks Block Dashboard

**Risk:** If all 9 services are slow, health check takes 45+ seconds (9 × 5s timeout).

**Impact:** Dashboard appears unresponsive; admins think it's broken.

**Mitigation:**
- Already using `asyncio.gather` for concurrent pings (max 5s total)
- Dashboard shows loading skeletons (visual feedback)
- Can reduce timeout from 5s to 3s if needed

**Status:** Low risk; concurrent pings keep response time under 10s.

## Success Metrics

**Operational KPIs:**
- Health check success rate > 99% (for running services)
- Dashboard uptime > 99.9%
- Average health check response time < 5 seconds
- Cost analytics load time < 3 seconds

**Adoption KPIs:**
- Number of active admin users (target: 3-5)
- Daily health checks performed (target: 10-20/day)
- LLM provider configurations (target: 2-3 providers)

**Quality KPIs:**
- Backend test pass rate = 100%
- Zero critical bugs in production
- Zero false positives in health checks

## Delivery Checklist

**Before production deployment:**

- [ ] All environment variables set (JWT secret, gateway key)
- [ ] PostgreSQL database running and accessible
- [ ] Redis running (optional but recommended)
- [ ] First admin user created via `/auth/setup`
- [ ] Backend running on port 8300
- [ ] Dashboard running on port 3300
- [ ] All 9 monitored services configured in `config.py`
- [ ] LLM Gateway running and reachable
- [ ] CORS allows dashboard origin (port 3300)
- [ ] Backup of `admin_users` table (critical credentials)

**Post-deployment validation:**

- [ ] Login works with first admin user
- [ ] Overview page shows correct KPIs
- [ ] Health checks show expected service status
- [ ] Provider list loads from gateway
- [ ] Cost analytics shows usage data
- [ ] Service overview shows all 9 services

## Support & Maintenance

**Monitoring:**
- Admin backend health: `http://localhost:8300/api/v1/health`
- PostgreSQL: Check `admin_users` and `admin_health_snapshots` tables
- Redis: Check key count in database 4

**Routine maintenance:**
- Rotate JWT secret quarterly (invalidates all sessions)
- Rotate LLM Gateway service key quarterly
- Clean up old health snapshots (keep last 30 days)
- Review admin user list (deactivate inactive admins)

**Troubleshooting:**
- **"Cannot connect to backend"** — Check backend is running on port 8300
- **"Gateway unavailable"** — Check LLM Gateway is running on port 8200
- **"All services down"** — Verify service URLs in `config.py`
- **"Invalid token"** — JWT secret may have been rotated; re-login

---
*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [QA Engineer Guide](QA_ENGINEER.md) · [End User Guide](END_USER.md)*
