# E2E Test Suite

Comprehensive end-to-end tests for the entire dropshipping platform and all SaaS services.

## Test Coverage

### Core Platform (ports 3000-3001)
- **Dashboard** (26 spec files): Full merchant workflow tests
- **Storefront** (7 spec files): Customer shopping experience tests

### SaaS Services
- **TrendScout** (port 3101): Product research and trend analysis
- **ContentForge** (port 3102): AI content generation
- **RankPilot** (port 3103): SEO rank tracking
- **FlowSend** (port 3104): Email marketing automation
- **SpyDrop** (port 3105): Competitor intelligence
- **PostPilot** (port 3106): Social media scheduling
- **AdScale** (port 3107): Ad campaign optimization
- **ShopChat** (port 3108): AI chatbot management
- **Admin** (port 3300): Super admin dashboard

## Running Tests

```bash
# Run all tests
make test-e2e

# Run specific service
npx playwright test --project=trendscout

# Run in UI mode
make test-e2e-ui

# Run in background
make test-e2e-bg
tail -f logs/test-runs/e2e-*.log
```

## Test Structure

Each service has tests covering:
1. **Authentication** - Register, login, logout, protected routes
2. **Core Features** - Primary service functionality
3. **API Keys** - API key management (where applicable)
4. **Billing** - Subscription and usage display
5. **Seed Data** - Validation of pre-populated demo data

## Prerequisites

All services must be running:
- Core backend: `make dev-backend` (port 8000)
- Core dashboards: `make dev-dashboard` (ports 3000-3001)
- SaaS services: `make dev-services` (ports 8101-8108, 3101-3108)
- Admin: `make dev-admin` (ports 8300, 3300)

## Writing New Tests

Follow existing patterns in `tests/service-helpers.ts`:
- Use `registerServiceUser()` for test isolation
- Use `serviceLogin()` for UI authentication
- Use `serviceApiPost/Get/Patch/Delete()` for API setup
- Always wait for `networkidle` after navigation
- Use generous timeouts for first assertions (10s)

## CI/CD Integration

Tests run with:
- Single worker (prevents system overload)
- 4GB Node heap limit
- Retry on failure (2x in CI)
- Video/screenshot on failure only
