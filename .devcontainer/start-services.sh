#!/bin/bash
# start-services.sh — Launches all platform services in the background.
# Called by devcontainer postStartCommand.
# Services: FastAPI backend (8000), Dashboard (3000), Storefront (3001)

set -e

LOG_DIR="/workspaces/ecomm/.devcontainer/logs"
mkdir -p "$LOG_DIR"

echo "==> Installing backend dependencies..."
cd /workspaces/ecomm/backend
pip install -e '.[dev]' --quiet 2>&1 | tail -1

echo "==> Running database migrations..."
alembic upgrade head 2>&1 | tail -3

echo "==> Starting FastAPI backend on port 8000..."
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload \
  > "$LOG_DIR/backend.log" 2>&1 &
echo $! > "$LOG_DIR/backend.pid"

echo "==> Installing dashboard dependencies..."
cd /workspaces/ecomm/dashboard
npm install --silent 2>&1 | tail -1

echo "==> Starting Dashboard on port 3000..."
nohup npm run dev > "$LOG_DIR/dashboard.log" 2>&1 &
echo $! > "$LOG_DIR/dashboard.pid"

echo "==> Installing storefront dependencies..."
cd /workspaces/ecomm/storefront
npm install --silent 2>&1 | tail -1

echo "==> Starting Storefront on port 3001..."
nohup npm run dev -- -p 3001 > "$LOG_DIR/storefront.log" 2>&1 &
echo $! > "$LOG_DIR/storefront.pid"

echo ""
echo "All services started:"
echo "  Backend API:  http://localhost:8000"
echo "  Dashboard:    http://localhost:3000"
echo "  Storefront:   http://localhost:3001"
echo ""
echo "Logs: $LOG_DIR/"
