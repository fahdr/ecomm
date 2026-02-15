# Implementation Steps

> Part of [Super Admin Dashboard](README.md) documentation

## Phase 1: Foundation

- [x] Create `admin/backend/` project structure with FastAPI application entry point (`app/main.py`)
- [x] Configure pydantic-settings (`app/config.py`) with `ADMIN_` env prefix, port 8300, Redis DB 4
- [x] Set up async SQLAlchemy database layer (`app/database.py`) sharing the main `dropshipping` PostgreSQL database
- [x] Add CORS middleware allowing all origins for dashboard communication
- [x] Implement basic health check endpoint at `GET /api/v1/health`
- [x] Wire auto-table-creation on startup via `Base.metadata.create_all`
- [x] Define `service_urls` config map for all 9 managed services (8 SaaS + LLM Gateway) with their base URLs and ports

## Phase 2: Authentication System

- [x] Create `AdminUser` model (`admin_users` table) with email, hashed password, role (super_admin/admin/viewer), is_active flag
- [x] Build auth service (`app/services/auth_service.py`) with bcrypt password hashing and verification
- [x] Implement JWT token creation and decoding using HS256 algorithm with `admin_secret_key`
- [x] Configure token expiration at 480 minutes (8 hours) via `admin_token_expire_minutes`
- [x] Build `get_current_admin` FastAPI dependency (`app/api/deps.py`) that extracts Bearer token, validates JWT, loads AdminUser, and checks `is_active`
- [x] Handle expired tokens, invalid signatures, missing subjects, and deactivated accounts with 401 responses
- [x] Implement `POST /api/v1/admin/auth/setup` one-time endpoint to create the first super_admin (returns 409 if any admin exists)
- [x] Implement `POST /api/v1/admin/auth/login` endpoint with email/password verification returning JWT
- [x] Implement `GET /api/v1/admin/auth/me` endpoint returning current admin profile (id, email, role, is_active)

## Phase 3: Health Monitoring

- [x] Create `ServiceHealthSnapshot` model (`admin_health_snapshots` table) with service_name, status (healthy/degraded/down), response_time_ms, checked_at
- [x] Add indexes on `service_name` and `checked_at` for efficient history queries
- [x] Build `_ping_service()` helper using httpx.AsyncClient with 5-second timeout to hit each service's `/api/v1/health` endpoint
- [x] Classify responses: HTTP 200 with `status: healthy` -> healthy, non-200 -> degraded, timeout/connection error -> down
- [x] Implement `GET /api/v1/admin/health/services` endpoint that pings all services concurrently via `asyncio.gather` and persists snapshots
- [x] Implement `GET /api/v1/admin/health/history` endpoint returning the last N snapshots (configurable limit 1-500) with optional service_name filter
- [x] Protect both health endpoints behind `get_current_admin` dependency

## Phase 4: LLM Gateway Proxy

- [x] Build HTTP proxy helpers (`_proxy_get`, `_proxy_post`, `_proxy_patch`, `_proxy_delete`) in `app/api/llm_proxy.py`
- [x] Configure proxy to forward requests to `settings.llm_gateway_url` with `X-Service-Key` header authentication
- [x] Set 10-second timeout for all proxy requests to the gateway
- [x] Handle gateway connection errors (502) and timeouts (504) with descriptive error messages
- [x] Implement `GET /api/v1/admin/llm/providers` proxying to gateway's provider list
- [x] Implement `POST /api/v1/admin/llm/providers` proxying provider creation to gateway
- [x] Implement `PATCH /api/v1/admin/llm/providers/{id}` proxying provider updates to gateway
- [x] Implement `DELETE /api/v1/admin/llm/providers/{id}` proxying provider deletion to gateway
- [x] Implement `GET /api/v1/admin/llm/usage/summary` proxying usage summary with configurable `days` param
- [x] Implement `GET /api/v1/admin/llm/usage/by-provider` proxying per-provider usage breakdown
- [x] Implement `GET /api/v1/admin/llm/usage/by-service` proxying per-service usage breakdown
- [x] Protect all LLM proxy endpoints behind `get_current_admin` dependency

## Phase 5: Service Overview

- [x] Build `_extract_port()` utility to parse port numbers from service URLs
- [x] Define `ServiceInfo` response schema with name, port, URL, last_status, last_response_time_ms, last_checked_at
- [x] Implement `GET /api/v1/admin/services` endpoint that lists all 9 managed services enriched with their most recent health snapshot
- [x] Return `unknown` status for services that have never been health-checked
- [x] Protect the services endpoint behind `get_current_admin` dependency

## Phase 6: Admin Dashboard (Next.js)

- [x] Create `admin/dashboard/` Next.js application with app router
- [x] Build admin shell layout component (`admin-shell.tsx`) with navigation sidebar
- [x] Build status badge component (`status-badge.tsx`) for healthy/degraded/down/unknown indicators
- [x] Build API client library (`src/lib/api.ts`) for authenticated requests to admin backend
- [x] Implement login page (`src/app/login/page.tsx`) with email/password form
- [x] Implement main dashboard page (`src/app/page.tsx`) showing service overview at a glance
- [x] Implement services page (`src/app/services/page.tsx`) with health status for all managed services
- [x] Implement providers page (`src/app/providers/page.tsx`) for LLM provider management
- [x] Implement costs page (`src/app/costs/page.tsx`) for LLM usage analytics and cost tracking

## Phase 7: Testing & Polish

- [x] Set up test infrastructure with schema-based isolation (`admin_test` schema)
- [x] Write auth endpoint tests (`test_auth.py`) covering setup, login, /me, invalid credentials, duplicate setup, deactivated accounts
- [x] Write health monitor tests (`test_health_monitor.py`) with mocked httpx responses for healthy, degraded, and down states
- [x] Write LLM proxy tests (`test_llm_proxy.py`) with mocked gateway responses for provider CRUD and usage analytics
- [x] Write services overview tests (`test_services_overview.py`) verifying service listing with and without health snapshots
- [x] Achieve 34 passing backend tests across all modules
- [x] Add comprehensive docstrings to every module, class, method, and function
- [x] Create documentation suite: README, ARCHITECTURE, API_REFERENCE, SETUP, TESTING, QA_ENGINEER, PROJECT_MANAGER, END_USER

---
*See also: [Setup](SETUP.md) · [Architecture](ARCHITECTURE.md) · [Testing](TESTING.md)*
