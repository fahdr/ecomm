#!/usr/bin/env bash
# Production startup script for the Dropshipping Platform + SaaS Suite.
#
# Runs database migrations, creates schemas, applies performance indexes,
# and starts the FastAPI backend with Gunicorn/Uvicorn workers.
#
# **For Developers:**
#   This script is called by the Docker ENTRYPOINT or Kubernetes init
#   container. It expects all environment variables (DATABASE_URL,
#   REDIS_URL, SENTRY_DSN, etc.) to be pre-configured.
#
# **For QA Engineers:**
#   After startup, hit GET /api/v1/health to verify the service is live.
#
# **For Project Managers:**
#   This is the single entrypoint for all production deployments.
#   It handles the complete bootstrap sequence so deploys are atomic.
#
# Usage:
#   ./scripts/start-production.sh [service]
#
# Examples:
#   ./scripts/start-production.sh              # Start core platform
#   ./scripts/start-production.sh trendscout   # Start TrendScout service

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE="${1:-dropshipping}"

# ── Configuration ────────────────────────────────────────────────────
WORKERS="${WORKERS:-4}"
HOST="${HOST:-0.0.0.0}"
LOG_LEVEL="${LOG_LEVEL:-info}"

# Service port mapping
declare -A SERVICE_PORTS=(
    [dropshipping]=8000
    [trendscout]=8101
    [contentforge]=8102
    [rankpilot]=8103
    [flowsend]=8104
    [spydrop]=8105
    [postpilot]=8106
    [adscale]=8107
    [shopchat]=8108
    [sourcepilot]=8109
    [llm-gateway]=8200
    [admin]=8300
)

PORT="${PORT:-${SERVICE_PORTS[$SERVICE]:-8000}}"

echo "========================================================"
echo "  Production Startup: $SERVICE"
echo "  Port: $PORT | Workers: $WORKERS | Log level: $LOG_LEVEL"
echo "========================================================"

# ── Step 1: Wait for database ────────────────────────────────────────
echo "[1/5] Waiting for database..."
MAX_RETRIES=30
RETRY_INTERVAL=2

for i in $(seq 1 $MAX_RETRIES); do
    if python -c "
import asyncio, asyncpg, os
async def check():
    dsn = os.environ.get('DATABASE_URL', '').replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(dsn)
    await conn.close()
asyncio.run(check())
" 2>/dev/null; then
        echo "  Database is ready."
        break
    fi

    if [ "$i" -eq "$MAX_RETRIES" ]; then
        echo "  ERROR: Database not reachable after $MAX_RETRIES attempts."
        exit 1
    fi
    echo "  Waiting for database... (attempt $i/$MAX_RETRIES)"
    sleep "$RETRY_INTERVAL"
done

# ── Step 2: Wait for Redis ───────────────────────────────────────────
echo "[2/5] Waiting for Redis..."
for i in $(seq 1 $MAX_RETRIES); do
    if python -c "
import redis, os
r = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
r.ping()
" 2>/dev/null; then
        echo "  Redis is ready."
        break
    fi

    if [ "$i" -eq "$MAX_RETRIES" ]; then
        echo "  WARNING: Redis not reachable. Continuing without cache."
        break
    fi
    echo "  Waiting for Redis... (attempt $i/$MAX_RETRIES)"
    sleep "$RETRY_INTERVAL"
done

# ── Step 3: Create database schemas ─────────────────────────────────
echo "[3/5] Creating database schemas..."
python -c "
import asyncio, asyncpg, os

SCHEMAS = [
    'public',
    'trendscout', 'contentforge', 'rankpilot', 'flowsend',
    'spydrop', 'postpilot', 'adscale', 'shopchat', 'sourcepilot',
    'llm_gateway', 'admin',
]

async def create_schemas():
    dsn = os.environ.get('DATABASE_URL', '').replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(dsn)
    for schema in SCHEMAS:
        try:
            await conn.execute(f'CREATE SCHEMA IF NOT EXISTS {schema}')
            print(f'  Schema ready: {schema}')
        except Exception as e:
            print(f'  Schema {schema}: {e}')
    await conn.close()

asyncio.run(create_schemas())
" || echo "  WARNING: Schema creation encountered errors (may already exist)."

# ── Step 4: Apply database indexes ───────────────────────────────────
echo "[4/5] Applying performance indexes..."
if [ "$SERVICE" = "dropshipping" ]; then
    python -c "
import asyncio
from app.indexes import apply_indexes
from app.database import engine

async def run():
    count = await apply_indexes(engine)
    print(f'  Applied {count} indexes.')
    await engine.dispose()

asyncio.run(run())
" 2>/dev/null || echo "  WARNING: Index application skipped (non-critical)."
else
    echo "  Skipped (indexes only apply to core platform)."
fi

# ── Step 5: Start the service ────────────────────────────────────────
echo "[5/5] Starting $SERVICE on port $PORT with $WORKERS workers..."
echo "========================================================"

# Determine the app module based on service
if [ "$SERVICE" = "dropshipping" ]; then
    APP_MODULE="app.main:app"
    WORK_DIR="$ROOT_DIR/dropshipping/backend"
elif [ "$SERVICE" = "llm-gateway" ]; then
    APP_MODULE="app.main:app"
    WORK_DIR="$ROOT_DIR/llm-gateway/backend"
elif [ "$SERVICE" = "admin" ]; then
    APP_MODULE="app.main:app"
    WORK_DIR="$ROOT_DIR/admin/backend"
else
    APP_MODULE="app.main:app"
    WORK_DIR="$ROOT_DIR/$SERVICE/backend"
fi

cd "$WORK_DIR"

exec uvicorn "$APP_MODULE" \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level "$LOG_LEVEL" \
    --access-log \
    --proxy-headers \
    --forwarded-allow-ips="*"
