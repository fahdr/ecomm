#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────
# Service Scaffold Script
#
# Creates a new fully independent service from the template by copying
# all files and replacing placeholder variables.
#
# For Developers:
#   ./scripts/scaffold.sh trendscout "TrendScout" "AI-Powered Product Research" 8101 3101 3201
#
# For Project Managers:
#   This script creates a complete, runnable service. After scaffolding,
#   the service has auth, billing, API keys, and infrastructure ready.
#   Only feature-specific code needs to be added.
#
# Usage:
#   scaffold.sh <name> <display_name> <tagline> <backend_port> <dashboard_port> <landing_port> \
#     <primary_color_oklch> <primary_hex> <accent_color_oklch> <accent_hex> \
#     <bg_color_oklch> <bg_hex> <heading_font> <body_font> \
#     <db_port> <redis_port>
# ──────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Argument parsing ─────────────────────────────────────────────
SERVICE_NAME="${1:?Usage: scaffold.sh <name> <display_name> <tagline> <backend_port> <dashboard_port> <landing_port>}"
SERVICE_DISPLAY_NAME="${2:?Missing display name}"
SERVICE_TAGLINE="${3:?Missing tagline}"
SERVICE_PORT="${4:?Missing backend port}"
DASHBOARD_PORT="${5:?Missing dashboard port}"
LANDING_PORT="${6:?Missing landing port}"
PRIMARY_COLOR="${7:-oklch(0.65 0.20 250)}"
PRIMARY_HEX="${8:-#3b82f6}"
ACCENT_COLOR="${9:-oklch(0.75 0.15 200)}"
ACCENT_HEX="${10:-#38bdf8}"
BG_COLOR="${11:-oklch(0.15 0.02 260)}"
BG_HEX="${12:-#0f172a}"
HEADING_FONT="${13:-Space Grotesk}"
BODY_FONT="${14:-Inter}"
DB_PORT="${15:-5432}"
REDIS_PORT="${16:-6379}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPLATE_DIR="$(dirname "$SCRIPT_DIR")"
SERVICES_DIR="$(dirname "$TEMPLATE_DIR")"
TARGET_DIR="${SERVICES_DIR}/${SERVICE_NAME}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Scaffolding: ${SERVICE_DISPLAY_NAME}"
echo "║  Directory:   ${TARGET_DIR}"
echo "║  Backend:     http://localhost:${SERVICE_PORT}"
echo "║  Dashboard:   http://localhost:${DASHBOARD_PORT}"
echo "║  Landing:     http://localhost:${LANDING_PORT}"
echo "╚══════════════════════════════════════════════════════════╝"

# ── Check target doesn't exist ───────────────────────────────────
if [ -d "$TARGET_DIR" ]; then
    echo "ERROR: Directory ${TARGET_DIR} already exists. Remove it first or choose a different name."
    exit 1
fi

# ── Copy template ────────────────────────────────────────────────
echo "→ Copying template..."
cp -r "$TEMPLATE_DIR" "$TARGET_DIR"

# Remove the scaffold script from the copy (it's a template tool, not a service file)
rm -rf "${TARGET_DIR}/scripts/scaffold.sh"

# ── Replace placeholders ────────────────────────────────────────
echo "→ Replacing placeholders..."

# Create lowercase tagline variant
SERVICE_TAGLINE_LOWER=$(echo "$SERVICE_TAGLINE" | tr '[:upper:]' '[:lower:]')

# Find all text files and replace placeholders
find "$TARGET_DIR" -type f \( \
    -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.json" -o \
    -name "*.yml" -o -name "*.yaml" -o -name "*.md" -o -name "*.ini" -o \
    -name "*.css" -o -name "*.mjs" -o -name "*.env*" -o -name "Makefile" -o \
    -name "Dockerfile" -o -name "*.mako" -o -name "*.toml" \
\) -exec sed -i \
    -e "s|{{SERVICE_NAME}}|${SERVICE_NAME}|g" \
    -e "s|{{SERVICE_DISPLAY_NAME}}|${SERVICE_DISPLAY_NAME}|g" \
    -e "s|{{SERVICE_TAGLINE}}|${SERVICE_TAGLINE}|g" \
    -e "s|{{SERVICE_TAGLINE_LOWER}}|${SERVICE_TAGLINE_LOWER}|g" \
    -e "s|{{SERVICE_PORT}}|${SERVICE_PORT}|g" \
    -e "s|{{DASHBOARD_PORT}}|${DASHBOARD_PORT}|g" \
    -e "s|{{LANDING_PORT}}|${LANDING_PORT}|g" \
    -e "s|{{PRIMARY_COLOR}}|${PRIMARY_COLOR}|g" \
    -e "s|{{PRIMARY_HEX}}|${PRIMARY_HEX}|g" \
    -e "s|{{ACCENT_COLOR}}|${ACCENT_COLOR}|g" \
    -e "s|{{ACCENT_HEX}}|${ACCENT_HEX}|g" \
    -e "s|{{BG_COLOR}}|${BG_COLOR}|g" \
    -e "s|{{BG_HEX}}|${BG_HEX}|g" \
    -e "s|{{HEADING_FONT}}|${HEADING_FONT}|g" \
    -e "s|{{BODY_FONT}}|${BODY_FONT}|g" \
    -e "s|{{DB_PORT}}|${DB_PORT}|g" \
    -e "s|{{REDIS_PORT}}|${REDIS_PORT}|g" \
    {} +

# ── Create empty alembic versions dir ───────────────────────────
mkdir -p "${TARGET_DIR}/backend/alembic/versions"

echo ""
echo "✓ Service '${SERVICE_DISPLAY_NAME}' scaffolded at: ${TARGET_DIR}"
echo ""
echo "Next steps:"
echo "  1. cd ${TARGET_DIR}"
echo "  2. make install        # Install dependencies"
echo "  3. make migrate        # Run database migrations"
echo "  4. make start          # Start all services"
echo "  5. Add feature-specific code to backend/app/api/, models/, services/"
echo ""
