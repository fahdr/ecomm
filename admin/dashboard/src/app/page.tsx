/**
 * Overview dashboard page for the Super Admin Dashboard.
 *
 * Displays the high-level platform health and usage metrics:
 *   - 3 KPI cards: Total Cost, Total Requests, Cache Hit Rate
 *   - Service health grid: 9 cards (8 services + gateway) with status
 *
 * For Developers:
 *   Data is fetched from:
 *     GET /llm/usage/summary — cost, request count, cache rate
 *     GET /health/services  — per-service health status
 *   Both endpoints are proxied through the admin backend.
 *
 * For QA Engineers:
 *   - Verify KPI cards display correct values from the API.
 *   - Verify service health cards show correct status badges.
 *   - Verify loading skeletons appear before data loads.
 *   - Verify error state displays when API is unreachable.
 *
 * For Project Managers:
 *   This is the landing page after login. It provides an
 *   at-a-glance view of platform health and LLM spending.
 *
 * For End Users:
 *   This page is exclusively for platform administrators.
 */

"use client";

import { useEffect, useState } from "react";
import {
  DollarSign,
  Zap,
  Database,
  Activity,
  Radio,
} from "lucide-react";
import * as motion from "motion/react-client";
import { AdminShell } from "@/components/admin-shell";
import { StatusBadge, type HealthStatus } from "@/components/status-badge";
import { adminApi } from "@/lib/api";

/**
 * Shape of the usage summary response from the admin API.
 */
interface UsageSummary {
  period_days: number;
  total_requests: number;
  total_cost_usd: number;
  total_tokens: number;
  cached_requests: number;
  error_requests: number;
  cache_hit_rate: number;
}

/**
 * Shape of a service health entry from the admin API.
 */
interface ServiceHealth {
  name: string;
  display_name: string;
  status: HealthStatus;
  port?: number;
  url?: string;
}

/**
 * Default service list when the API doesn't return health data.
 * Covers the 8 SaaS services plus the LLM Gateway itself.
 */
const DEFAULT_SERVICES: ServiceHealth[] = [
  { name: "llm-gateway", display_name: "LLM Gateway", status: "unknown", port: 8200 },
  { name: "shopchat", display_name: "ShopChat", status: "unknown", port: 8101 },
  { name: "contentforge", display_name: "ContentForge", status: "unknown", port: 8102 },
  { name: "adscale", display_name: "AdScale", status: "unknown", port: 8103 },
  { name: "rankpilot", display_name: "RankPilot", status: "unknown", port: 8104 },
  { name: "spydrop", display_name: "SpyDrop", status: "unknown", port: 8105 },
  { name: "trendscout", display_name: "TrendScout", status: "unknown", port: 8106 },
  { name: "flowsend", display_name: "FlowSend", status: "unknown", port: 8107 },
  { name: "postpilot", display_name: "PostPilot", status: "unknown", port: 8108 },
];

/**
 * Overview dashboard page component.
 *
 * Fetches usage summary and service health data on mount,
 * then renders KPI cards and a service health grid.
 *
 * @returns The overview dashboard page JSX.
 */
export default function OverviewPage() {
  /** Usage summary data from the API. */
  const [summary, setSummary] = useState<UsageSummary | null>(null);

  /** Service health data. Falls back to defaults if API unavailable. */
  const [services, setServices] = useState<ServiceHealth[]>(DEFAULT_SERVICES);

  /** Loading state for initial data fetch. */
  const [loading, setLoading] = useState(true);

  /**
   * Fetch dashboard data on mount.
   */
  useEffect(() => {
    async function fetchData() {
      try {
        const [summaryData, healthData] = await Promise.allSettled([
          adminApi.get<UsageSummary>("/llm/usage/summary"),
          adminApi.get<{ services: ServiceHealth[] }>("/health/services"),
        ]);

        if (summaryData.status === "fulfilled") {
          setSummary(summaryData.value);
        }

        if (healthData.status === "fulfilled" && healthData.value?.services) {
          setServices(healthData.value.services);
        }
      } catch {
        /* Silently handle — UI shows fallback state. */
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  /**
   * Format a USD value for display.
   *
   * @param value - The dollar amount.
   * @returns Formatted string like "$12.45" or "$1,234.56".
   */
  const formatCost = (value: number): string => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  /**
   * Format a large number with commas.
   *
   * @param value - The number to format.
   * @returns Formatted string like "1,234,567".
   */
  const formatNumber = (value: number): string => {
    return new Intl.NumberFormat("en-US").format(value);
  };

  /** KPI card definitions derived from the usage summary. */
  const kpiCards = [
    {
      label: "Total Cost",
      value: summary ? formatCost(summary.total_cost_usd) : "--",
      subtitle: `Last ${summary?.period_days || 30} days`,
      icon: DollarSign,
      color: "var(--admin-accent)",
    },
    {
      label: "Total Requests",
      value: summary ? formatNumber(summary.total_requests) : "--",
      subtitle: `${summary?.error_requests || 0} errors`,
      icon: Zap,
      color: "var(--admin-primary)",
    },
    {
      label: "Cache Hit Rate",
      value: summary ? `${summary.cache_hit_rate}%` : "--",
      subtitle: `${formatNumber(summary?.cached_requests || 0)} cached`,
      icon: Database,
      color: "var(--admin-success)",
    },
  ];

  return (
    <AdminShell>
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Page header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <div className="flex items-center gap-3 mb-1">
            <Activity size={20} className="text-[var(--admin-primary)]" />
            <h1 className="text-lg font-semibold text-[var(--admin-text-primary)]">
              Platform Overview
            </h1>
            <span className="ml-auto flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-[var(--admin-text-muted)]">
              <Radio size={10} className="animate-pulse-glow text-[var(--admin-success)]" />
              Live
            </span>
          </div>
          <p className="text-sm text-[var(--admin-text-muted)]">
            System health and LLM usage metrics
          </p>
        </motion.div>

        {/* KPI cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {kpiCards.map((kpi, index) => (
            <motion.div
              key={kpi.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.1 * index }}
              className="admin-card p-5"
            >
              <div className="flex items-start justify-between mb-3">
                <span className="text-xs font-medium text-[var(--admin-text-muted)] uppercase tracking-wider">
                  {kpi.label}
                </span>
                <kpi.icon
                  size={18}
                  style={{ color: kpi.color }}
                  className="opacity-70"
                />
              </div>
              <div
                className="font-data text-2xl font-bold mb-1"
                style={{ color: kpi.color }}
              >
                {loading ? (
                  <div className="h-8 w-28 bg-[var(--admin-bg-surface)] rounded animate-pulse" />
                ) : (
                  kpi.value
                )}
              </div>
              <p className="text-xs text-[var(--admin-text-muted)]">
                {kpi.subtitle}
              </p>
            </motion.div>
          ))}
        </div>

        {/* Service health grid */}
        <div>
          <h2 className="text-sm font-semibold text-[var(--admin-text-secondary)] mb-4 uppercase tracking-wider">
            Service Health
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {services.map((service, index) => (
              <motion.div
                key={service.name}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, delay: 0.05 * index }}
                className="admin-card p-4 flex items-center justify-between"
              >
                <div className="min-w-0">
                  <h3 className="text-sm font-medium text-[var(--admin-text-primary)] truncate">
                    {service.display_name}
                  </h3>
                  {service.port && (
                    <p className="font-data text-[11px] text-[var(--admin-text-muted)] mt-0.5">
                      :{service.port}
                    </p>
                  )}
                </div>
                {loading ? (
                  <div className="w-16 h-5 bg-[var(--admin-bg-surface)] rounded-full animate-pulse" />
                ) : (
                  <StatusBadge status={service.status} size="sm" />
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </AdminShell>
  );
}
