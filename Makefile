# Makefile — Dropshipping Platform developer workflow
#
# Common targets for starting services, running tests, seeding data,
# and cleaning up zombie processes.
#
# **For Developers:**
#   Run `make help` to see all available targets.
#   Most targets can be combined: `make clean start seed`
#
# **For QA Engineers:**
#   `make test` runs backend + e2e tests with memory limits.
#   `make test-backend` and `make test-e2e` run individually.
#
# **Resource limits:**
#   Tests are capped at 4GB Node heap to keep total RAM under 6GB
#   (servers + DB + Redis use ~2GB). Servers run without limits.

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Paths
ROOT        := /workspaces/ecomm
BACKEND     := $(ROOT)/backend
DASHBOARD   := $(ROOT)/dashboard
STOREFRONT  := $(ROOT)/storefront
E2E         := $(ROOT)/e2e
SCRIPTS     := $(ROOT)/scripts
LOG_DIR     := $(ROOT)/.devcontainer/logs

# Database
DB_USER     := dropship
DB_PASS     := dropship_dev
DB_NAME     := dropshipping
DB_HOST     := db
PSQL        := PGPASSWORD=$(DB_PASS) psql -h $(DB_HOST) -U $(DB_USER) -d $(DB_NAME)

# Memory limits for tests (keep total under 6GB with servers running)
NODE_TEST_MEM := --max-old-space-size=4096

# ──────────────────────────────────────────────────────────────────
# Help
# ──────────────────────────────────────────────────────────────────

.PHONY: help
help: ## Show this help message
	@echo ""
	@echo "Dropshipping Platform — Development Workflow"
	@echo "─────────────────────────────────────────────"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ──────────────────────────────────────────────────────────────────
# Process Management
# ──────────────────────────────────────────────────────────────────

.PHONY: clean
clean: ## Kill zombie/orphan Node and Uvicorn processes
	@echo "==> Killing zombie processes..."
	@-pkill -f "uvicorn app.main:app" 2>/dev/null || true
	@-pkill -f "next dev" 2>/dev/null || true
	@-pkill -f "next-router-worker" 2>/dev/null || true
	@-pkill -f "playwright" 2>/dev/null || true
	@-rm -f $(DASHBOARD)/.next/dev/lock 2>/dev/null || true
	@-rm -f $(STOREFRONT)/.next/dev/lock 2>/dev/null || true
	@-rm -f $(LOG_DIR)/*.pid 2>/dev/null || true
	@sleep 1
	@echo "  Done. All service processes killed."

.PHONY: status
status: ## Show running services and their PIDs
	@echo "==> Service status:"
	@echo -n "  Backend (uvicorn):  " && (pgrep -f "uvicorn app.main:app" | tr '\n' ' ' || echo "not running") && echo ""
	@echo -n "  Dashboard (next):   " && (pgrep -f "next dev.*3000" | head -1 || echo "not running") && echo ""
	@echo -n "  Storefront (next):  " && (pgrep -f "next dev.*3001\\|next-router-worker" | head -1 || echo "not running") && echo ""
	@echo ""
	@echo "==> Port check:"
	@-ss -tlnp 2>/dev/null | grep -E ':(8000|3000|3001) ' || echo "  No services listening"

# ──────────────────────────────────────────────────────────────────
# Start / Stop Services
# ──────────────────────────────────────────────────────────────────

.PHONY: start
start: ## Start all services (backend, dashboard, storefront)
	@bash $(ROOT)/.devcontainer/start-services.sh

.PHONY: start-backend
start-backend: ## Start only the FastAPI backend
	@echo "==> Starting backend on port 8000..."
	@mkdir -p $(LOG_DIR)
	@cd $(BACKEND) && nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload \
		> $(LOG_DIR)/backend.log 2>&1 &
	@echo "  Backend started. Log: $(LOG_DIR)/backend.log"

.PHONY: start-dashboard
start-dashboard: ## Start only the dashboard (port 3000)
	@echo "==> Starting dashboard on port 3000..."
	@mkdir -p $(LOG_DIR)
	@cd $(DASHBOARD) && nohup npm run dev > $(LOG_DIR)/dashboard.log 2>&1 &
	@echo "  Dashboard started. Log: $(LOG_DIR)/dashboard.log"

.PHONY: start-storefront
start-storefront: ## Start only the storefront (port 3001)
	@echo "==> Starting storefront on port 3001..."
	@mkdir -p $(LOG_DIR)
	@cd $(STOREFRONT) && nohup npm run dev -- -p 3001 > $(LOG_DIR)/storefront.log 2>&1 &
	@echo "  Storefront started. Log: $(LOG_DIR)/storefront.log"

.PHONY: restart
restart: clean start ## Kill all processes and restart services

.PHONY: stop
stop: clean ## Stop all services (alias for clean)

# ──────────────────────────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────────────────────────

.PHONY: db-migrate
db-migrate: ## Run Alembic migrations
	@echo "==> Running migrations..."
	@cd $(BACKEND) && alembic upgrade head
	@echo "  Migrations complete."

.PHONY: db-truncate
db-truncate: ## Truncate all data tables (keeps schema)
	@echo "==> Truncating all tables..."
	@$(PSQL) -c " \
		DO \$$\$$ \
		DECLARE r RECORD; \
		BEGIN \
			FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename != 'alembic_version') LOOP \
				EXECUTE 'TRUNCATE TABLE ' || quote_ident(r.tablename) || ' CASCADE'; \
			END LOOP; \
		END \$$\$$;" 2>&1
	@echo "  All tables truncated."

.PHONY: db-reset
db-reset: db-truncate db-migrate ## Truncate tables and re-run migrations

.PHONY: db-shell
db-shell: ## Open psql shell to the database
	@$(PSQL)

# ──────────────────────────────────────────────────────────────────
# Seed Data
# ──────────────────────────────────────────────────────────────────

.PHONY: seed
seed: ## Seed the database with demo data
	@echo "==> Seeding database..."
	@cd $(ROOT) && npx tsx $(SCRIPTS)/seed.ts
	@echo "  Seed complete."

.PHONY: reseed
reseed: db-truncate seed ## Truncate all data then seed fresh

# ──────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────

.PHONY: test
test: test-backend test-e2e ## Run all tests (backend + e2e)

.PHONY: test-backend
test-backend: ## Run backend pytest suite
	@echo "==> Running backend tests..."
	@cd $(BACKEND) && python -m pytest tests/ -x -q --tb=short
	@echo ""

.PHONY: test-e2e
test-e2e: ## Run Playwright E2E tests (memory-limited)
	@echo "==> Running E2E tests (heap limited to 4GB)..."
	@cd $(E2E) && NODE_OPTIONS="$(NODE_TEST_MEM)" npx playwright test --reporter=list
	@echo ""

.PHONY: test-e2e-ui
test-e2e-ui: ## Run E2E tests with Playwright UI
	@cd $(E2E) && NODE_OPTIONS="$(NODE_TEST_MEM)" npx playwright test --ui

.PHONY: test-e2e-file
test-e2e-file: ## Run a single E2E spec file (usage: make test-e2e-file F=tests/dashboard/auth.spec.ts)
	@cd $(E2E) && NODE_OPTIONS="$(NODE_TEST_MEM)" npx playwright test $(F) --reporter=list

# ──────────────────────────────────────────────────────────────────
# Background / Detached Tests (survives session disconnect)
# ──────────────────────────────────────────────────────────────────

TEST_LOG_DIR := $(LOG_DIR)/test-runs
TIMESTAMP    = $(shell date +%Y%m%d-%H%M%S)

.PHONY: test-backend-bg
test-backend-bg: ## Run backend tests detached in background (logs to file)
	@mkdir -p $(TEST_LOG_DIR)
	@echo "==> Running backend tests in background..."
	@nohup bash -c 'cd $(BACKEND) && python -m pytest tests/ -x -q --tb=short \
		> $(TEST_LOG_DIR)/pytest-$(TIMESTAMP).log 2>&1; \
		echo "EXIT_CODE=$$?" >> $(TEST_LOG_DIR)/pytest-$(TIMESTAMP).log' \
		> /dev/null 2>&1 &
	@echo "  PID: $$!"
	@echo "  Log: $(TEST_LOG_DIR)/pytest-$(TIMESTAMP).log"
	@echo "  Follow: tail -f $(TEST_LOG_DIR)/pytest-$(TIMESTAMP).log"

.PHONY: test-e2e-bg
test-e2e-bg: ## Run E2E tests detached in background (logs to file)
	@mkdir -p $(TEST_LOG_DIR)
	@echo "==> Running E2E tests in background (heap limited to 4GB)..."
	@nohup bash -c 'cd $(E2E) && NODE_OPTIONS="$(NODE_TEST_MEM)" npx playwright test --reporter=list \
		> $(TEST_LOG_DIR)/e2e-$(TIMESTAMP).log 2>&1; \
		echo "EXIT_CODE=$$?" >> $(TEST_LOG_DIR)/e2e-$(TIMESTAMP).log' \
		> /dev/null 2>&1 &
	@echo "  PID: $$!"
	@echo "  Log: $(TEST_LOG_DIR)/e2e-$(TIMESTAMP).log"
	@echo "  Follow: tail -f $(TEST_LOG_DIR)/e2e-$(TIMESTAMP).log"

.PHONY: test-all-bg
test-all-bg: ## Run backend + E2E tests sequentially in background
	@mkdir -p $(TEST_LOG_DIR)
	@echo "==> Running all tests in background (backend then E2E)..."
	@nohup bash -c '\
		LOG=$(TEST_LOG_DIR)/all-$(TIMESTAMP).log; \
		echo "=== Backend Tests ===" > $$LOG; \
		cd $(BACKEND) && python -m pytest tests/ -x -q --tb=short >> $$LOG 2>&1; \
		PYTEST_RC=$$?; \
		echo "" >> $$LOG; \
		echo "=== E2E Tests ===" >> $$LOG; \
		cd $(E2E) && NODE_OPTIONS="$(NODE_TEST_MEM)" npx playwright test --reporter=list >> $$LOG 2>&1; \
		E2E_RC=$$?; \
		echo "" >> $$LOG; \
		echo "=== Summary ===" >> $$LOG; \
		echo "Backend: exit $$PYTEST_RC" >> $$LOG; \
		echo "E2E: exit $$E2E_RC" >> $$LOG; \
		echo "Finished: $$(date)" >> $$LOG' \
		> /dev/null 2>&1 &
	@echo "  PID: $$!"
	@echo "  Log: $(TEST_LOG_DIR)/all-$(TIMESTAMP).log"
	@echo "  Follow: tail -f $(TEST_LOG_DIR)/all-$(TIMESTAMP).log"

.PHONY: test-logs
test-logs: ## Show latest test run log
	@ls -t $(TEST_LOG_DIR)/*.log 2>/dev/null | head -1 | xargs cat 2>/dev/null || echo "No test logs found. Run make test-backend-bg or make test-e2e-bg first."

.PHONY: test-status
test-status: ## Check if background tests are still running
	@echo "==> Background test processes:"
	@-pgrep -af "pytest|playwright test" 2>/dev/null || echo "  No tests running."
	@echo ""
	@echo "==> Latest test logs:"
	@ls -lt $(TEST_LOG_DIR)/*.log 2>/dev/null | head -5 || echo "  No test logs found."

# ──────────────────────────────────────────────────────────────────
# Build
# ──────────────────────────────────────────────────────────────────

.PHONY: build
build: build-dashboard build-storefront ## Build dashboard and storefront

.PHONY: build-dashboard
build-dashboard: ## Build the dashboard for production
	@echo "==> Building dashboard..."
	@cd $(DASHBOARD) && npm run build
	@echo "  Dashboard build complete."

.PHONY: build-storefront
build-storefront: ## Build the storefront for production
	@echo "==> Building storefront..."
	@cd $(STOREFRONT) && npm run build
	@echo "  Storefront build complete."

# ──────────────────────────────────────────────────────────────────
# Logs
# ──────────────────────────────────────────────────────────────────

.PHONY: logs
logs: ## Tail all service logs
	@tail -f $(LOG_DIR)/backend.log $(LOG_DIR)/dashboard.log $(LOG_DIR)/storefront.log

.PHONY: logs-backend
logs-backend: ## Tail backend log
	@tail -f $(LOG_DIR)/backend.log

.PHONY: logs-dashboard
logs-dashboard: ## Tail dashboard log
	@tail -f $(LOG_DIR)/dashboard.log

.PHONY: logs-storefront
logs-storefront: ## Tail storefront log
	@tail -f $(LOG_DIR)/storefront.log

# ──────────────────────────────────────────────────────────────────
# Composite Workflows
# ──────────────────────────────────────────────────────────────────

.PHONY: fresh
fresh: clean db-truncate start seed ## Full reset: kill procs, truncate, start services, seed

.PHONY: ci
ci: test-backend build test-e2e ## CI pipeline: backend tests → build → e2e tests
