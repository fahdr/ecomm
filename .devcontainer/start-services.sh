#!/bin/bash
# start-services.sh — Launches core platform services in the background.
# Called by devcontainer postStartCommand.
#
# Core services (always started):
#   - FastAPI backend (8000)
#   - Dashboard (3000)
#   - Storefront (3001)
#
# SaaS services, LLM Gateway, Admin, and Master Landing are started on demand
# via `make start-svc S=<name>`, `make start-llm-gateway`, etc.
#
# To start everything: `make start-all`

set -e

LOG_DIR="/workspaces/ecomm/.devcontainer/logs"
mkdir -p "$LOG_DIR"

# ── Shared packages ──────────────────────────────────────────────────────────
echo "==> Installing shared packages..."
cd /workspaces/ecomm/packages/py-core
pip install -e '.[dev]' --quiet 2>&1 | tail -1
cd /workspaces/ecomm/packages/py-connectors
pip install -e '.[dev]' --quiet 2>&1 | tail -1

# ── Core backend ─────────────────────────────────────────────────────────────
echo "==> Installing backend dependencies..."
cd /workspaces/ecomm/dropshipping/backend
pip install -e '.[dev]' --quiet 2>&1 | tail -1

echo "==> Running database migrations..."
alembic upgrade head 2>&1 | tail -3

echo "==> Starting FastAPI backend on port 8000..."
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload \
  > "$LOG_DIR/backend.log" 2>&1 &
echo $! > "$LOG_DIR/backend.pid"

# ── Dashboard ────────────────────────────────────────────────────────────────
echo "==> Installing dashboard dependencies..."
cd /workspaces/ecomm/dropshipping/dashboard
npm install --silent 2>&1 | tail -1

echo "==> Starting Dashboard on port 3000..."
nohup npm run dev > "$LOG_DIR/dashboard.log" 2>&1 &
echo $! > "$LOG_DIR/dashboard.pid"

# ── Storefront ───────────────────────────────────────────────────────────────
echo "==> Installing storefront dependencies..."
cd /workspaces/ecomm/dropshipping/storefront
npm install --silent 2>&1 | tail -1

echo "==> Starting Storefront on port 3001..."
nohup npm run dev -- -p 3001 > "$LOG_DIR/storefront.log" 2>&1 &
echo $! > "$LOG_DIR/storefront.pid"

# ── E2E test dependencies ────────────────────────────────────────────────────
echo "==> Installing e2e test dependencies..."
cd /workspaces/ecomm/e2e
npm install --silent 2>&1 | tail -1
npx playwright install --with-deps chromium 2>&1 | tail -1

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "Core services started:"
echo "  Backend API:  http://localhost:8000"
echo "  Dashboard:    http://localhost:3000"
echo "  Storefront:   http://localhost:3001"
echo ""
echo "To start SaaS services:"
echo "  make start-trendscout    # TrendScout (8101/3101/3201)"
echo "  make start-contentforge  # ContentForge (8102/3102/3202)"
echo "  make start-rankpilot     # RankPilot (8103/3103/3203)"
echo "  make start-flowsend      # FlowSend (8104/3104/3204)"
echo "  make start-spydrop       # SpyDrop (8105/3105/3205)"
echo "  make start-postpilot     # PostPilot (8106/3106/3206)"
echo "  make start-adscale       # AdScale (8107/3107/3207)"
echo "  make start-shopchat      # ShopChat (8108/3108/3208)"
echo "  make start-all           # Start everything"
echo ""
echo "Logs: $LOG_DIR/"
