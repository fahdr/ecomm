# Pre-Launch Checklist

> **Phase 7: Polish & Launch Prep**
>
> Complete every item before the beta launch. Each section must be signed
> off by the responsible owner. Items are ordered by dependency — complete
> earlier sections before later ones.

---

## 1. Infrastructure Ready

- [ ] PostgreSQL 16 provisioned with production-grade resources (CPU, RAM, IOPS)
- [ ] Redis 7 cluster deployed with persistence enabled (AOF + RDB)
- [ ] All 12 database schemas created (`make db-create-schemas`)
- [ ] Performance indexes applied (`make db-create-indexes`)
- [ ] Kubernetes namespace `ecomm` created with resource quotas
- [ ] Helm charts validated for core platform + 9 SaaS services
- [ ] Docker images built and pushed to GHCR for all services
- [ ] Horizontal Pod Autoscaler configured for backend services
- [ ] Ingress controller configured with TLS termination
- [ ] DNS records pointing to load balancer (A/CNAME)
- [ ] CDN configured for static assets (dashboards, storefronts, landing pages)
- [ ] Celery workers and Beat scheduler deployed
- [ ] Redis connection pools sized appropriately per service

## 2. Security Verified

- [ ] `SecurityHeadersMiddleware` active on all 12 backend services
- [ ] Rate limiting enabled (`100/min` default, `5/min` on auth endpoints)
- [ ] JWT secret keys rotated and stored in Kubernetes secrets
- [ ] Stripe webhook secrets configured per environment
- [ ] CORS origins restricted to production domains only
- [ ] HTTPS enforced on all endpoints (HSTS header active)
- [ ] Database credentials stored in sealed secrets (not env vars)
- [ ] API key hashing verified in `ecomm_core` auth module
- [ ] No `.env` files or credentials committed to the repository
- [ ] Dependency vulnerability scan clean (`pip audit`, `npm audit`)
- [ ] Content-Security-Policy headers set appropriately for each frontend
- [ ] OAuth2 token expiry verified (15 min access, 7 day refresh)

## 3. Monitoring Active

- [ ] Sentry DSN configured for all backend services
- [ ] Sentry environment labels set (`production`, `staging`)
- [ ] Error alerting rules configured (Slack/PagerDuty integration)
- [ ] Request logging middleware (`RequestLoggingMiddleware`) active on all services
- [ ] Health check endpoints responding on all 12 backends
- [ ] Kubernetes liveness and readiness probes configured
- [ ] Uptime monitoring configured for critical endpoints
- [ ] Log aggregation pipeline active (stdout -> collector -> storage)
- [ ] Performance baselines recorded for key endpoints (P50, P95, P99)
- [ ] Database connection pool metrics visible

## 4. Data Prepared

- [ ] Production database migrated to latest schema
- [ ] Default plan limits configured (Free, Starter, Growth, Pro)
- [ ] Stripe products and prices created for all subscription tiers
- [ ] Stripe webhook endpoints registered for production domain
- [ ] Seed data loaded for demo/beta accounts (if applicable)
- [ ] LLM Gateway API keys configured for AI providers
- [ ] Email templates verified for transactional emails (welcome, order confirmation)
- [ ] Default store themes and presets available (11 presets, 13 block types)

## 5. Legal Complete

- [ ] Terms of Service published and linked from signup flow
- [ ] Privacy Policy published and linked from signup flow
- [ ] Cookie consent banner implemented (if applicable to region)
- [ ] GDPR data export endpoint functional (`/api/v1/exports/`)
- [ ] Data retention policy documented
- [ ] Stripe billing terms disclosed to merchants
- [ ] Acceptable Use Policy published for SaaS services

## 6. Testing Complete

- [ ] All ~2,000 backend tests passing across 12 services
- [ ] All frontend builds succeeding (22 Next.js apps)
- [ ] E2E test suite passing (62 spec files, 12 Playwright projects)
- [ ] CI pipeline green on main branch
- [ ] Load testing completed for critical paths (checkout, product listing)
- [ ] Cross-browser testing completed (Chrome, Firefox, Safari, Edge)
- [ ] Mobile responsiveness verified on dashboard and storefront
- [ ] Onboarding checklist flow tested end-to-end
- [ ] Billing flow tested with Stripe test mode

## 7. Go-Live Steps

> Execute these in order on launch day.

- [ ] Merge `feat/phase7-polish` branch to `main`
- [ ] Tag release: `git tag v1.0.0 && git push --tags`
- [ ] Verify CD pipeline completes (`.github/workflows/deploy.yml`)
- [ ] Verify all pods are healthy: `kubectl -n ecomm get pods`
- [ ] Verify health endpoints: `curl https://api.example.com/api/v1/health`
- [ ] Run smoke test: register user -> create store -> add product -> place order
- [ ] Enable Sentry alerting (un-mute production environment)
- [ ] Announce beta launch to initial users
- [ ] Monitor error rates for first 24 hours
- [ ] Review Sentry dashboard for any unhandled exceptions

---

## Sign-Off

| Section | Owner | Date | Status |
|---------|-------|------|--------|
| Infrastructure | DevOps | | Pending |
| Security | Security Lead | | Pending |
| Monitoring | SRE | | Pending |
| Data | Backend Lead | | Pending |
| Legal | Legal/Compliance | | Pending |
| Testing | QA Lead | | Pending |
| Go-Live | Engineering Manager | | Pending |
