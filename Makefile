# Makefile — Dropshipping Platform + SaaS Suite developer workflow
#
# Monorepo structure:
#   dropshipping/ — Core platform (backend, dashboard, storefront)
#   trendscout/, contentforge/, ... — 8 standalone SaaS services
#   packages/ — Shared libraries (py-core, py-connectors)
#   llm-gateway/ — Centralized LLM microservice
#   admin/ — Super admin dashboard
#   master-landing/ — Suite landing page
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

# Paths — monorepo layout
ROOT           := /workspaces/ecomm
PLATFORM       := $(ROOT)/dropshipping
BACKEND        := $(PLATFORM)/backend
DASHBOARD      := $(PLATFORM)/dashboard
STOREFRONT     := $(PLATFORM)/storefront
E2E            := $(ROOT)/e2e
SCRIPTS        := $(ROOT)/scripts
LOG_DIR        := $(ROOT)/.devcontainer/logs

# Infrastructure services
LLM_GATEWAY    := $(ROOT)/llm-gateway
ADMIN          := $(ROOT)/admin
MASTER_LANDING := $(ROOT)/master-landing

# SaaS services list
SERVICES       := trendscout contentforge rankpilot flowsend spydrop postpilot adscale shopchat

# SaaS service port mappings (backend / dashboard / landing)
PORT_trendscout   := 8101 3101 3201
PORT_contentforge := 8102 3102 3202
PORT_rankpilot    := 8103 3103 3203
PORT_flowsend     := 8104 3104 3204
PORT_spydrop      := 8105 3105 3205
PORT_postpilot    := 8106 3106 3206
PORT_adscale      := 8107 3107 3207
PORT_shopchat     := 8108 3108 3208

# Database
DB_USER        := dropship
DB_PASS        := dropship_dev
DB_NAME        := dropshipping
DB_HOST        := db
PSQL           := PGPASSWORD=$(DB_PASS) psql -h $(DB_HOST) -U $(DB_USER) -d $(DB_NAME)

# Memory limits for tests (keep total under 6GB with servers running)
NODE_TEST_MEM  := --max-old-space-size=4096

# ──────────────────────────────────────────────────────────────────
# Help
# ──────────────────────────────────────────────────────────────────

.PHONY: help
help: ## Show this help message
	@echo ""
	@echo "Dropshipping Platform + SaaS Suite — Development Workflow"
	@echo "──────────────────────────────────────────────────────────"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'
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
	@-pkill -f "celery" 2>/dev/null || true
	@-pkill -f "playwright" 2>/dev/null || true
	@-rm -f $(DASHBOARD)/.next/dev/lock 2>/dev/null || true
	@-rm -f $(STOREFRONT)/.next/dev/lock 2>/dev/null || true
	@for svc in $(SERVICES); do \
		rm -f $(ROOT)/$$svc/dashboard/.next/dev/lock 2>/dev/null || true; \
		rm -f $(ROOT)/$$svc/landing/.next/dev/lock 2>/dev/null || true; \
	done
	@-rm -f $(ADMIN)/dashboard/.next/dev/lock 2>/dev/null || true
	@-rm -f $(LOG_DIR)/*.pid 2>/dev/null || true
	@sleep 1
	@echo "  Done. All service processes killed."

.PHONY: status
status: ## Show running services and their PIDs
	@echo "==> Core Platform:"
	@echo -n "  Backend     (8000):  " && (pgrep -f "uvicorn.*--port 8000" | tr '\n' ' ' || echo "not running") && echo ""
	@echo -n "  Dashboard   (3000):  " && (pgrep -f "next dev.*3000" | head -1 || echo "not running") && echo ""
	@echo -n "  Storefront  (3001):  " && (pgrep -f "next dev.*3001" | head -1 || echo "not running") && echo ""
	@echo ""
	@echo "==> Infrastructure:"
	@echo -n "  LLM Gateway (8200):  " && (pgrep -f "uvicorn.*--port 8200" | tr '\n' ' ' || echo "not running") && echo ""
	@echo -n "  Admin API   (8300):  " && (pgrep -f "uvicorn.*--port 8300" | tr '\n' ' ' || echo "not running") && echo ""
	@echo -n "  Admin Dash  (3300):  " && (pgrep -f "next dev.*3300" | head -1 || echo "not running") && echo ""
	@echo -n "  Landing     (3200):  " && (pgrep -f "next.*3200" | head -1 || echo "not running") && echo ""
	@echo ""
	@echo "==> SaaS Services:"
	@for svc in $(SERVICES); do \
		port=$$(echo $(PORT_$$svc) | cut -d' ' -f1 2>/dev/null); \
		echo -n "  $$svc ($$port): "; \
		pgrep -f "uvicorn.*--port $$port" > /dev/null 2>&1 && echo "running" || echo "not running"; \
	done
	@echo ""
	@echo "==> Port check:"
	@-ss -tlnp 2>/dev/null | grep -E ':(8000|8101|8102|8103|8104|8105|8106|8107|8108|8200|8300|3000|3001|3101|3102|3103|3104|3105|3106|3107|3108|3200|3201|3202|3203|3204|3205|3206|3207|3208|3300) ' || echo "  No services listening"

# ──────────────────────────────────────────────────────────────────
# Start / Stop — Core Platform
# ──────────────────────────────────────────────────────────────────

.PHONY: start
start: ## Start core platform (backend, dashboard, storefront)
	@bash $(ROOT)/.devcontainer/start-services.sh

.PHONY: start-all
start-all: start start-llm-gateway start-admin start-master-landing start-saas ## Start everything (core + infra + all SaaS)

.PHONY: start-backend
start-backend: ## Start only the FastAPI backend (port 8000)
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
restart: clean start ## Kill all processes and restart core services

.PHONY: restart-all
restart-all: clean start-all ## Kill all processes and restart everything

.PHONY: stop
stop: clean ## Stop all services (alias for clean)

# ──────────────────────────────────────────────────────────────────
# Start / Stop — LLM Gateway
# ──────────────────────────────────────────────────────────────────

.PHONY: start-llm-gateway
start-llm-gateway: ## Start LLM Gateway backend (port 8200)
	@echo "==> Starting LLM Gateway on port 8200..."
	@mkdir -p $(LOG_DIR)
	@cd $(LLM_GATEWAY)/backend && nohup uvicorn app.main:app --host 0.0.0.0 --port 8200 --reload \
		> $(LOG_DIR)/llm-gateway.log 2>&1 &
	@echo "  LLM Gateway started. Log: $(LOG_DIR)/llm-gateway.log"

# ──────────────────────────────────────────────────────────────────
# Start / Stop — Admin Dashboard
# ──────────────────────────────────────────────────────────────────

.PHONY: start-admin
start-admin: start-admin-backend start-admin-dashboard ## Start Admin (backend + dashboard)

.PHONY: start-admin-backend
start-admin-backend: ## Start Admin backend (port 8300)
	@echo "==> Starting Admin backend on port 8300..."
	@mkdir -p $(LOG_DIR)
	@cd $(ADMIN)/backend && nohup uvicorn app.main:app --host 0.0.0.0 --port 8300 --reload \
		> $(LOG_DIR)/admin-backend.log 2>&1 &
	@echo "  Admin backend started. Log: $(LOG_DIR)/admin-backend.log"

.PHONY: start-admin-dashboard
start-admin-dashboard: ## Start Admin dashboard (port 3300)
	@echo "==> Starting Admin dashboard on port 3300..."
	@mkdir -p $(LOG_DIR)
	@cd $(ADMIN)/dashboard && nohup npm run dev > $(LOG_DIR)/admin-dashboard.log 2>&1 &
	@echo "  Admin dashboard started. Log: $(LOG_DIR)/admin-dashboard.log"

# ──────────────────────────────────────────────────────────────────
# Start / Stop — Master Landing Page
# ──────────────────────────────────────────────────────────────────

.PHONY: start-master-landing
start-master-landing: ## Start master landing page (port 3200)
	@echo "==> Starting master landing on port 3200..."
	@mkdir -p $(LOG_DIR)
	@cd $(MASTER_LANDING) && nohup npm run dev > $(LOG_DIR)/master-landing.log 2>&1 &
	@echo "  Master landing started. Log: $(LOG_DIR)/master-landing.log"

# ──────────────────────────────────────────────────────────────────
# Start / Stop — SaaS Services
# ──────────────────────────────────────────────────────────────────

.PHONY: start-saas
start-saas: ## Start all 8 SaaS service backends
	@echo "==> Starting all SaaS service backends..."
	@mkdir -p $(LOG_DIR)
	@for svc in $(SERVICES); do \
		port=$$(echo $${svc} | awk '{ \
			if ($$0=="trendscout") print 8101; \
			else if ($$0=="contentforge") print 8102; \
			else if ($$0=="rankpilot") print 8103; \
			else if ($$0=="flowsend") print 8104; \
			else if ($$0=="spydrop") print 8105; \
			else if ($$0=="postpilot") print 8106; \
			else if ($$0=="adscale") print 8107; \
			else if ($$0=="shopchat") print 8108; \
		}'); \
		echo "  Starting $$svc backend on port $$port..."; \
		cd $(ROOT)/$$svc/backend && nohup uvicorn app.main:app --host 0.0.0.0 --port $$port --reload \
			> $(LOG_DIR)/$$svc-backend.log 2>&1 & \
	done
	@echo "  All SaaS backends started."

.PHONY: start-svc
start-svc: ## Start a specific SaaS service (usage: make start-svc S=trendscout)
	@if [ -z "$(S)" ]; then echo "Usage: make start-svc S=<service>"; exit 1; fi
	@port=$$(echo $(S) | awk '{ \
		if ($$0=="trendscout") print 8101; \
		else if ($$0=="contentforge") print 8102; \
		else if ($$0=="rankpilot") print 8103; \
		else if ($$0=="flowsend") print 8104; \
		else if ($$0=="spydrop") print 8105; \
		else if ($$0=="postpilot") print 8106; \
		else if ($$0=="adscale") print 8107; \
		else if ($$0=="shopchat") print 8108; \
	}'); \
	dash_port=$$(echo $(S) | awk '{ \
		if ($$0=="trendscout") print 3101; \
		else if ($$0=="contentforge") print 3102; \
		else if ($$0=="rankpilot") print 3103; \
		else if ($$0=="flowsend") print 3104; \
		else if ($$0=="spydrop") print 3105; \
		else if ($$0=="postpilot") print 3106; \
		else if ($$0=="adscale") print 3107; \
		else if ($$0=="shopchat") print 3108; \
	}'); \
	land_port=$$(echo $(S) | awk '{ \
		if ($$0=="trendscout") print 3201; \
		else if ($$0=="contentforge") print 3202; \
		else if ($$0=="rankpilot") print 3203; \
		else if ($$0=="flowsend") print 3204; \
		else if ($$0=="spydrop") print 3205; \
		else if ($$0=="postpilot") print 3206; \
		else if ($$0=="adscale") print 3207; \
		else if ($$0=="shopchat") print 3208; \
	}'); \
	mkdir -p $(LOG_DIR); \
	echo "==> Starting $(S) backend on port $$port..."; \
	cd $(ROOT)/$(S)/backend && nohup uvicorn app.main:app --host 0.0.0.0 --port $$port --reload \
		> $(LOG_DIR)/$(S)-backend.log 2>&1 & \
	echo "==> Starting $(S) dashboard on port $$dash_port..."; \
	cd $(ROOT)/$(S)/dashboard && nohup npm run dev -- -p $$dash_port \
		> $(LOG_DIR)/$(S)-dashboard.log 2>&1 & \
	echo "==> Starting $(S) landing on port $$land_port..."; \
	cd $(ROOT)/$(S)/landing && nohup npm run dev -- -p $$land_port \
		> $(LOG_DIR)/$(S)-landing.log 2>&1 & \
	echo "  $(S) started (backend: $$port, dashboard: $$dash_port, landing: $$land_port)"

# Named shortcuts for each SaaS service (backend + dashboard + landing)
.PHONY: start-trendscout
start-trendscout: ## Start TrendScout (8101/3101/3201)
	@$(MAKE) start-svc S=trendscout

.PHONY: start-contentforge
start-contentforge: ## Start ContentForge (8102/3102/3202)
	@$(MAKE) start-svc S=contentforge

.PHONY: start-rankpilot
start-rankpilot: ## Start RankPilot (8103/3103/3203)
	@$(MAKE) start-svc S=rankpilot

.PHONY: start-flowsend
start-flowsend: ## Start FlowSend (8104/3104/3204)
	@$(MAKE) start-svc S=flowsend

.PHONY: start-spydrop
start-spydrop: ## Start SpyDrop (8105/3105/3205)
	@$(MAKE) start-svc S=spydrop

.PHONY: start-postpilot
start-postpilot: ## Start PostPilot (8106/3106/3206)
	@$(MAKE) start-svc S=postpilot

.PHONY: start-adscale
start-adscale: ## Start AdScale (8107/3107/3207)
	@$(MAKE) start-svc S=adscale

.PHONY: start-shopchat
start-shopchat: ## Start ShopChat (8108/3108/3208)
	@$(MAKE) start-svc S=shopchat

# ──────────────────────────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────────────────────────

.PHONY: db-migrate
db-migrate: ## Run Alembic migrations (core platform)
	@echo "==> Running core platform migrations..."
	@cd $(BACKEND) && alembic upgrade head
	@echo "  Migrations complete."

.PHONY: db-migrate-all
db-migrate-all: db-migrate ## Run migrations for core + all SaaS services
	@for svc in $(SERVICES); do \
		echo "==> Running $$svc migrations..."; \
		cd $(ROOT)/$$svc/backend && alembic upgrade head 2>&1 || true; \
		echo ""; \
	done
	@echo "  All migrations complete."

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
seed: ## Seed all services with demo data (core + SaaS)
	@echo "==> Seeding all services..."
	@cd $(ROOT) && npx tsx $(SCRIPTS)/seed.ts
	@echo "  Seed complete."

.PHONY: seed-core
seed-core: ## Seed only core platform (dropshipping)
	@echo "==> Seeding core platform..."
	@cd $(ROOT) && SEED_CORE_ONLY=1 npx tsx $(SCRIPTS)/seed.ts
	@echo "  Core seed complete."

.PHONY: seed-svc
seed-svc: ## Seed a specific SaaS service (usage: make seed-svc S=trendscout)
	@if [ -z "$(S)" ]; then echo "Usage: make seed-svc S=<service>"; echo "  Services: trendscout contentforge rankpilot flowsend spydrop postpilot adscale shopchat"; exit 1; fi
	@echo "==> Seeding $(S)..."
	@cd $(ROOT) && SEED_SERVICE=$(S) npx tsx $(SCRIPTS)/seed.ts
	@echo "  $(S) seed complete."

.PHONY: seed-admin
seed-admin: ## Seed only the Admin dashboard
	@echo "==> Seeding Admin..."
	@cd $(ROOT) && SEED_ADMIN_ONLY=1 npx tsx $(SCRIPTS)/seed.ts
	@echo "  Admin seed complete."

.PHONY: seed-trendscout
seed-trendscout: ## Seed TrendScout demo data
	@cd $(ROOT) && SEED_SERVICE=trendscout npx tsx $(SCRIPTS)/seed.ts

.PHONY: seed-contentforge
seed-contentforge: ## Seed ContentForge demo data
	@cd $(ROOT) && SEED_SERVICE=contentforge npx tsx $(SCRIPTS)/seed.ts

.PHONY: seed-rankpilot
seed-rankpilot: ## Seed RankPilot demo data
	@cd $(ROOT) && SEED_SERVICE=rankpilot npx tsx $(SCRIPTS)/seed.ts

.PHONY: seed-flowsend
seed-flowsend: ## Seed FlowSend demo data
	@cd $(ROOT) && SEED_SERVICE=flowsend npx tsx $(SCRIPTS)/seed.ts

.PHONY: seed-spydrop
seed-spydrop: ## Seed SpyDrop demo data
	@cd $(ROOT) && SEED_SERVICE=spydrop npx tsx $(SCRIPTS)/seed.ts

.PHONY: seed-postpilot
seed-postpilot: ## Seed PostPilot demo data
	@cd $(ROOT) && SEED_SERVICE=postpilot npx tsx $(SCRIPTS)/seed.ts

.PHONY: seed-adscale
seed-adscale: ## Seed AdScale demo data
	@cd $(ROOT) && SEED_SERVICE=adscale npx tsx $(SCRIPTS)/seed.ts

.PHONY: seed-shopchat
seed-shopchat: ## Seed ShopChat demo data
	@cd $(ROOT) && SEED_SERVICE=shopchat npx tsx $(SCRIPTS)/seed.ts

.PHONY: reseed
reseed: db-truncate seed ## Truncate all data then seed fresh

# ──────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────

.PHONY: test
test: test-backend test-e2e ## Run all tests (backend + e2e)

.PHONY: test-all
test-all: test-backend test-services test-gateway test-admin test-e2e ## Run every test suite

.PHONY: test-backend
test-backend: ## Run core backend pytest suite
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

.PHONY: test-service
test-service: ## Run tests for a specific service (usage: make test-service S=trendscout)
	@echo "==> Running $(S) backend tests..."
	@cd $(ROOT)/$(S)/backend && python -m pytest tests/ -x -q --tb=short
	@echo ""

.PHONY: test-services
test-services: ## Run tests for all 8 SaaS services
	@for svc in $(SERVICES); do \
		echo "==> Testing $$svc..."; \
		cd $(ROOT)/$$svc/backend && python -m pytest tests/ -x -q --tb=short || exit 1; \
		echo ""; \
	done

.PHONY: test-gateway
test-gateway: ## Run LLM Gateway tests
	@echo "==> Running LLM Gateway tests..."
	@cd $(LLM_GATEWAY)/backend && python -m pytest tests/ -x -q --tb=short
	@echo ""

.PHONY: test-admin
test-admin: ## Run Admin dashboard tests
	@echo "==> Running Admin tests..."
	@cd $(ADMIN)/backend && python -m pytest tests/ -x -q --tb=short
	@echo ""

.PHONY: test-packages
test-packages: ## Run shared packages tests (py-core, py-connectors)
	@echo "==> Running py-core tests..."
	@cd $(ROOT)/packages/py-core && python -m pytest tests/ -x -q --tb=short
	@echo ""
	@echo "==> Running py-connectors tests..."
	@cd $(ROOT)/packages/py-connectors && python -m pytest tests/ -x -q --tb=short
	@echo ""

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

.PHONY: test-services-bg
test-services-bg: ## Run all SaaS service tests in background
	@mkdir -p $(TEST_LOG_DIR)
	@echo "==> Running all SaaS tests in background..."
	@nohup bash -c '\
		LOG=$(TEST_LOG_DIR)/services-$(TIMESTAMP).log; \
		for svc in $(SERVICES); do \
			echo "=== $$svc ===" >> $$LOG; \
			cd $(ROOT)/$$svc/backend && python -m pytest tests/ -x -q --tb=short >> $$LOG 2>&1; \
			echo "EXIT_CODE=$$?" >> $$LOG; \
			echo "" >> $$LOG; \
		done; \
		echo "Finished: $$(date)" >> $$LOG' \
		> /dev/null 2>&1 &
	@echo "  PID: $$!"
	@echo "  Log: $(TEST_LOG_DIR)/services-$(TIMESTAMP).log"
	@echo "  Follow: tail -f $(TEST_LOG_DIR)/services-$(TIMESTAMP).log"

.PHONY: test-all-bg
test-all-bg: ## Run all tests sequentially in background (core + services + e2e)
	@mkdir -p $(TEST_LOG_DIR)
	@echo "==> Running all tests in background..."
	@nohup bash -c '\
		LOG=$(TEST_LOG_DIR)/all-$(TIMESTAMP).log; \
		echo "=== Core Backend Tests ===" > $$LOG; \
		cd $(BACKEND) && python -m pytest tests/ -x -q --tb=short >> $$LOG 2>&1; \
		CORE_RC=$$?; \
		echo "" >> $$LOG; \
		echo "=== LLM Gateway Tests ===" >> $$LOG; \
		cd $(LLM_GATEWAY)/backend && python -m pytest tests/ -x -q --tb=short >> $$LOG 2>&1; \
		GW_RC=$$?; \
		echo "" >> $$LOG; \
		echo "=== Admin Tests ===" >> $$LOG; \
		cd $(ADMIN)/backend && python -m pytest tests/ -x -q --tb=short >> $$LOG 2>&1; \
		ADM_RC=$$?; \
		echo "" >> $$LOG; \
		for svc in $(SERVICES); do \
			echo "=== $$svc Tests ===" >> $$LOG; \
			cd $(ROOT)/$$svc/backend && python -m pytest tests/ -x -q --tb=short >> $$LOG 2>&1; \
			echo "EXIT_CODE=$$?" >> $$LOG; \
			echo "" >> $$LOG; \
		done; \
		echo "=== E2E Tests ===" >> $$LOG; \
		cd $(E2E) && NODE_OPTIONS="$(NODE_TEST_MEM)" npx playwright test --reporter=list >> $$LOG 2>&1; \
		E2E_RC=$$?; \
		echo "" >> $$LOG; \
		echo "=== Summary ===" >> $$LOG; \
		echo "Core Backend: exit $$CORE_RC" >> $$LOG; \
		echo "LLM Gateway:  exit $$GW_RC" >> $$LOG; \
		echo "Admin:        exit $$ADM_RC" >> $$LOG; \
		echo "E2E:          exit $$E2E_RC" >> $$LOG; \
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
build: build-dashboard build-storefront ## Build core dashboard and storefront

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

.PHONY: build-admin
build-admin: ## Build Admin dashboard for production
	@echo "==> Building Admin dashboard..."
	@cd $(ADMIN)/dashboard && npm run build
	@echo "  Admin dashboard build complete."

.PHONY: build-master-landing
build-master-landing: ## Build master landing page for production
	@echo "==> Building master landing..."
	@cd $(MASTER_LANDING) && npm run build
	@echo "  Master landing build complete."

.PHONY: build-svc
build-svc: ## Build a specific SaaS service (usage: make build-svc S=trendscout)
	@echo "==> Building $(S) dashboard..."
	@cd $(ROOT)/$(S)/dashboard && npm run build
	@echo "==> Building $(S) landing..."
	@cd $(ROOT)/$(S)/landing && npm run build
	@echo "  $(S) build complete."

.PHONY: build-all
build-all: build build-admin build-master-landing ## Build all frontends (core + admin + landing)
	@for svc in $(SERVICES); do \
		echo "==> Building $$svc dashboard..."; \
		cd $(ROOT)/$$svc/dashboard && npm run build 2>&1 || true; \
		echo "==> Building $$svc landing..."; \
		cd $(ROOT)/$$svc/landing && npm run build 2>&1 || true; \
	done
	@echo "  All builds complete."

# ──────────────────────────────────────────────────────────────────
# Install Dependencies
# ──────────────────────────────────────────────────────────────────

.PHONY: install
install: ## Install dependencies for core platform
	@echo "==> Installing core backend..."
	@cd $(BACKEND) && pip install -e '.[dev]' --quiet
	@echo "==> Installing dashboard..."
	@cd $(DASHBOARD) && npm install --silent
	@echo "==> Installing storefront..."
	@cd $(STOREFRONT) && npm install --silent
	@echo "  Core install complete."

.PHONY: install-all
install-all: install ## Install dependencies for all services
	@echo "==> Installing shared packages..."
	@cd $(ROOT)/packages/py-core && pip install -e '.[dev]' --quiet
	@cd $(ROOT)/packages/py-connectors && pip install -e '.[dev]' --quiet
	@echo "==> Installing LLM Gateway..."
	@cd $(LLM_GATEWAY)/backend && pip install -e '.[dev]' --quiet
	@echo "==> Installing Admin..."
	@cd $(ADMIN)/backend && pip install -e '.[dev]' --quiet
	@cd $(ADMIN)/dashboard && npm install --silent
	@echo "==> Installing Master Landing..."
	@cd $(MASTER_LANDING) && npm install --silent
	@for svc in $(SERVICES); do \
		echo "==> Installing $$svc..."; \
		cd $(ROOT)/$$svc/backend && pip install -e '.[dev]' --quiet 2>&1 || true; \
		cd $(ROOT)/$$svc/dashboard && npm install --silent 2>&1 || true; \
		cd $(ROOT)/$$svc/landing && npm install --silent 2>&1 || true; \
	done
	@echo "  All installs complete."

# ──────────────────────────────────────────────────────────────────
# Logs
# ──────────────────────────────────────────────────────────────────

.PHONY: logs
logs: ## Tail all core service logs
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

.PHONY: logs-llm-gateway
logs-llm-gateway: ## Tail LLM Gateway log
	@tail -f $(LOG_DIR)/llm-gateway.log

.PHONY: logs-admin
logs-admin: ## Tail Admin logs
	@tail -f $(LOG_DIR)/admin-backend.log $(LOG_DIR)/admin-dashboard.log

.PHONY: logs-svc
logs-svc: ## Tail a specific SaaS service log (usage: make logs-svc S=trendscout)
	@tail -f $(LOG_DIR)/$(S)-backend.log

.PHONY: logs-all
logs-all: ## Tail all available logs
	@tail -f $(LOG_DIR)/*.log

# ──────────────────────────────────────────────────────────────────
# Composite Workflows
# ──────────────────────────────────────────────────────────────────

.PHONY: fresh
fresh: clean db-truncate start seed ## Full reset: kill procs, truncate, start core, seed

.PHONY: fresh-all
fresh-all: clean db-truncate start-all seed ## Full reset: kill procs, truncate, start everything, seed

.PHONY: ci
ci: test-backend build test-e2e ## CI pipeline: backend tests -> build -> e2e tests

.PHONY: ci-full
ci-full: test-all build-all ## Full CI: all tests -> all builds
