#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────
# Scaffold All 8 Service Products
#
# Creates all service products from the template with their unique
# branding, colors, fonts, and port assignments.
#
# For Developers:
#   Run this once to generate all 8 services. Then add feature-specific
#   code to each service individually.
#
# For Project Managers:
#   This creates the foundation for all 8 standalone products.
#   Each service will have auth, billing, and infrastructure ready.
#
# Usage:
#   ./scripts/scaffold-all-services.sh
# ──────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCAFFOLD="${SCRIPT_DIR}/../services/_template/scripts/scaffold.sh"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         Scaffolding All 8 Service Products                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# ── A1: TrendScout ───────────────────────────────────────────────
# Product Research — Electric Blue on Dark Navy
"$SCAFFOLD" \
    "trendscout" \
    "TrendScout" \
    "AI-Powered Product Research" \
    8101 3101 3201 \
    "oklch(0.65 0.20 250)" "#3b82f6" \
    "oklch(0.75 0.15 200)" "#38bdf8" \
    "oklch(0.15 0.02 260)" "#0f172a" \
    "Space Grotesk" "Inter" \
    5501 6401

# ── A2: ContentForge ────────────────────────────────────────────
# AI Content Generator — Violet Purple on Deep Charcoal
"$SCAFFOLD" \
    "contentforge" \
    "ContentForge" \
    "AI Product Content Generator" \
    8102 3102 3202 \
    "oklch(0.60 0.22 300)" "#8b5cf6" \
    "oklch(0.75 0.18 280)" "#a78bfa" \
    "oklch(0.14 0.02 280)" "#1e1b2e" \
    "Clash Display" "Satoshi" \
    5502 6402

# ── A3: RankPilot ───────────────────────────────────────────────
# SEO Automation — Emerald Green on Off-white
"$SCAFFOLD" \
    "rankpilot" \
    "RankPilot" \
    "Automated SEO Engine" \
    8103 3103 3203 \
    "oklch(0.65 0.18 155)" "#10b981" \
    "oklch(0.72 0.15 140)" "#34d399" \
    "oklch(0.16 0.02 160)" "#0a1f1a" \
    "General Sans" "Inter" \
    5503 6403

# ── A4: FlowSend ────────────────────────────────────────────────
# Email Marketing — Coral Red on Warm White
"$SCAFFOLD" \
    "flowsend" \
    "FlowSend" \
    "Smart Email Marketing" \
    8104 3104 3204 \
    "oklch(0.65 0.20 25)" "#f43f5e" \
    "oklch(0.75 0.18 40)" "#fb923c" \
    "oklch(0.15 0.02 20)" "#1f0f0f" \
    "Satoshi" "Inter" \
    5504 6404

# ── A5: SpyDrop ─────────────────────────────────────────────────
# Competitor Intelligence — Slate Cyan on Dark Slate
"$SCAFFOLD" \
    "spydrop" \
    "SpyDrop" \
    "Competitor Intelligence" \
    8105 3105 3205 \
    "oklch(0.60 0.15 220)" "#06b6d4" \
    "oklch(0.70 0.12 210)" "#67e8f9" \
    "oklch(0.14 0.02 230)" "#0c1826" \
    "Geist" "Geist" \
    5505 6405

# ── A6: PostPilot ───────────────────────────────────────────────
# Social Media Automation — Hot Pink on Light Gray
"$SCAFFOLD" \
    "postpilot" \
    "PostPilot" \
    "Social Media Automation" \
    8106 3106 3206 \
    "oklch(0.65 0.22 350)" "#ec4899" \
    "oklch(0.72 0.18 330)" "#f472b6" \
    "oklch(0.15 0.03 340)" "#1f0a1a" \
    "Plus Jakarta Sans" "Inter" \
    5506 6406

# ── A7: AdScale ─────────────────────────────────────────────────
# Ad Campaign Manager — Amber Gold on Rich Black
"$SCAFFOLD" \
    "adscale" \
    "AdScale" \
    "AI Ad Campaign Manager" \
    8107 3107 3207 \
    "oklch(0.72 0.18 80)" "#f59e0b" \
    "oklch(0.78 0.15 60)" "#fbbf24" \
    "oklch(0.14 0.02 80)" "#1a1508" \
    "Inter Tight" "Inter" \
    5507 6407

# ── A8: ShopChat ────────────────────────────────────────────────
# AI Shopping Assistant — Indigo on Soft Lavender
"$SCAFFOLD" \
    "shopchat" \
    "ShopChat" \
    "AI Shopping Assistant" \
    8108 3108 3208 \
    "oklch(0.55 0.20 275)" "#6366f1" \
    "oklch(0.70 0.18 290)" "#818cf8" \
    "oklch(0.14 0.03 280)" "#13111f" \
    "Outfit" "Inter" \
    5508 6408

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  ✓ All 8 services scaffolded successfully!                    ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║                                                                ║"
echo "║  Service         Backend   Dashboard  Landing                  ║"
echo "║  ─────────────── ───────── ────────── ────────                 ║"
echo "║  TrendScout      :8101     :3101      :3201                    ║"
echo "║  ContentForge    :8102     :3102      :3202                    ║"
echo "║  RankPilot       :8103     :3103      :3203                    ║"
echo "║  FlowSend        :8104     :3104      :3204                    ║"
echo "║  SpyDrop         :8105     :3105      :3205                    ║"
echo "║  PostPilot       :8106     :3106      :3206                    ║"
echo "║  AdScale         :8107     :3107      :3207                    ║"
echo "║  ShopChat        :8108     :3108      :3208                    ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
