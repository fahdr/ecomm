# SpyDrop — Development Commands
#
# For Developers:
#   make start     — Start all services locally
#   make test      — Run all tests
#   make migrate   — Run database migrations
#
# For QA Engineers:
#   make test-backend  — Run backend unit tests
#   make test-e2e      — Run end-to-end tests
#
# For Project Managers:
#   make fresh     — Full reset and restart

.PHONY: help start stop backend dashboard landing worker beat test test-backend migrate seed fresh clean

SERVICE_NAME := spydrop
BACKEND_PORT := 8105
DASHBOARD_PORT := 3105

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Start Services ───────────────────────────────────────────────

start: backend dashboard landing worker ## Start all services
	@echo "✓ All services started"
	@echo "  Backend:   http://localhost:$(BACKEND_PORT)"
	@echo "  Dashboard: http://localhost:$(DASHBOARD_PORT)"
	@echo "  API Docs:  http://localhost:$(BACKEND_PORT)/docs"

backend: ## Start backend API server
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT) &

dashboard: ## Start dashboard dev server
	cd dashboard && npm run dev -- -p $(DASHBOARD_PORT) &

landing: ## Start landing page dev server
	cd landing && npm run dev -- -p 3205 &

worker: ## Start Celery worker
	cd backend && celery -A app.tasks.celery_app worker --loglevel=info -Q $(SERVICE_NAME) &

beat: ## Start Celery beat scheduler
	cd backend && celery -A app.tasks.celery_app beat --loglevel=info &

# ── Database ─────────────────────────────────────────────────────

migrate: ## Run database migrations
	cd backend && alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MSG="description")
	cd backend && alembic revision --autogenerate -m "$(MSG)"

db-reset: ## Reset database (truncate all tables)
	cd backend && python -c "from app.database import engine; import asyncio; from sqlalchemy import text; asyncio.run(engine.begin().__aenter__().then(lambda c: c.execute(text('DROP SCHEMA public CASCADE; CREATE SCHEMA public;'))))"
	$(MAKE) migrate

# ── Testing ──────────────────────────────────────────────────────

test: test-backend ## Run all tests

test-backend: ## Run backend unit tests
	cd backend && pytest -v

# ── Build ────────────────────────────────────────────────────────

build: ## Build all services for production
	cd dashboard && npm run build
	cd landing && npm run build

# ── Utilities ────────────────────────────────────────────────────

install: ## Install all dependencies
	cd backend && pip install -r requirements.txt
	cd dashboard && npm install
	cd landing && npm install

clean: ## Stop all background processes
	-pkill -f "uvicorn app.main:app.*$(BACKEND_PORT)" 2>/dev/null || true
	-pkill -f "celery.*$(SERVICE_NAME)" 2>/dev/null || true
	-pkill -f "next.*$(DASHBOARD_PORT)" 2>/dev/null || true
	@echo "✓ All processes stopped"

fresh: clean migrate start ## Full reset: stop, migrate, start
	@echo "✓ Fresh start complete"

docker-up: ## Start with Docker Compose
	docker-compose up -d

docker-down: ## Stop Docker Compose
	docker-compose down

docker-logs: ## Show Docker Compose logs
	docker-compose logs -f
