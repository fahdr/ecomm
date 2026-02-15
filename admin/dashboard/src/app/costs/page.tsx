/**
 * Cost analytics page for the Super Admin Dashboard.
 *
 * Displays LLM usage costs broken down by provider and service:
 *   - Summary stats bar: total cost, total requests, total tokens
 *   - By-provider breakdown table
 *   - By-service breakdown table
 *
 * For Developers:
 *   API endpoints used:
 *     GET /llm/usage/summary      — aggregate totals
 *     GET /llm/usage/by-provider   — cost grouped by LLM provider
 *     GET /llm/usage/by-service    — cost grouped by calling service
 *
 * For QA Engineers:
 *   - Verify tables render correct data from API.
 *   - Verify "no data" states appear when there are no usage logs.
 *   - Verify number formatting (currency, commas, percentages).
 *
 * For Project Managers:
 *   This page answers "how much are we spending on AI and where?"
 *   It breaks down costs by AI provider and by which service
 *   is consuming the most tokens.
 *
 * For End Users:
 *   This page is exclusively for platform administrators.
 */

"use client";

import { useEffect, useState } from "react";
import { DollarSign, Zap, Coins, BarChart3 } from "lucide-react";
import * as motion from "motion/react-client";
import { AdminShell } from "@/components/admin-shell";
import { adminApi } from "@/lib/api";

/**
 * Shape of the usage summary response.
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
 * Shape of a by-provider usage entry.
 */
interface ProviderUsage {
  provider_name: string;
  request_count: number;
  total_cost_usd: number;
  avg_latency_ms: number;
  total_tokens: number;
}

/**
 * Shape of a by-service usage entry.
 */
interface ServiceUsage {
  service_name: string;
  request_count: number;
  total_cost_usd: number;
  total_tokens: number;
}

/**
 * Cost analytics page component.
 *
 * Fetches usage summary, by-provider, and by-service breakdowns
 * on mount and renders them as stat cards and data tables.
 *
 * @returns The costs page JSX.
 */
export default function CostsPage() {
  /** Usage summary data. */
  const [summary, setSummary] = useState<UsageSummary | null>(null);

  /** Usage broken down by LLM provider. */
  const [byProvider, setByProvider] = useState<ProviderUsage[]>([]);

  /** Usage broken down by calling service. */
  const [byService, setByService] = useState<ServiceUsage[]>([]);

  /** Loading state for the initial fetch. */
  const [loading, setLoading] = useState(true);

  /**
   * Fetch all cost data on mount.
   */
  useEffect(() => {
    async function fetchData() {
      try {
        const [summaryRes, providerRes, serviceRes] =
          await Promise.allSettled([
            adminApi.get<UsageSummary>("/llm/usage/summary"),
            adminApi.get<ProviderUsage[]>("/llm/usage/by-provider"),
            adminApi.get<ServiceUsage[]>("/llm/usage/by-service"),
          ]);

        if (summaryRes.status === "fulfilled") setSummary(summaryRes.value);
        if (providerRes.status === "fulfilled")
          setByProvider(providerRes.value || []);
        if (serviceRes.status === "fulfilled")
          setByService(serviceRes.value || []);
      } catch {
        /* Silently handle — tables show empty state. */
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
   * @returns Formatted string like "$12.45".
   */
  const formatCost = (value: number): string =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 4,
    }).format(value);

  /**
   * Format a number with commas.
   *
   * @param value - The number to format.
   * @returns Formatted string like "1,234,567".
   */
  const formatNumber = (value: number): string =>
    new Intl.NumberFormat("en-US").format(value);

  /**
   * Calculate the percentage share of a value in a total.
   *
   * @param value - The numerator.
   * @param total - The denominator.
   * @returns Formatted percentage string like "42.1%".
   */
  const pct = (value: number, total: number): string =>
    total > 0 ? `${((value / total) * 100).toFixed(1)}%` : "0%";

  /** Summary stat cards. */
  const statCards = [
    {
      label: "Total Spend",
      value: summary ? formatCost(summary.total_cost_usd) : "--",
      icon: DollarSign,
      color: "var(--admin-accent)",
    },
    {
      label: "Total Requests",
      value: summary ? formatNumber(summary.total_requests) : "--",
      icon: Zap,
      color: "var(--admin-primary)",
    },
    {
      label: "Total Tokens",
      value: summary ? formatNumber(summary.total_tokens) : "--",
      icon: Coins,
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
            <BarChart3 size={20} className="text-[var(--admin-primary)]" />
            <h1 className="text-lg font-semibold text-[var(--admin-text-primary)]">
              Cost Analytics
            </h1>
          </div>
          <p className="text-sm text-[var(--admin-text-muted)]">
            LLM usage and spend breakdown for the last{" "}
            {summary?.period_days || 30} days
          </p>
        </motion.div>

        {/* Summary stat cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {statCards.map((stat, index) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.1 * index }}
              className="admin-card p-5"
            >
              <div className="flex items-start justify-between mb-3">
                <span className="text-xs font-medium text-[var(--admin-text-muted)] uppercase tracking-wider">
                  {stat.label}
                </span>
                <stat.icon
                  size={18}
                  style={{ color: stat.color }}
                  className="opacity-70"
                />
              </div>
              <div
                className="font-data text-2xl font-bold"
                style={{ color: stat.color }}
              >
                {loading ? (
                  <div className="h-8 w-24 bg-[var(--admin-bg-surface)] rounded animate-pulse" />
                ) : (
                  stat.value
                )}
              </div>
            </motion.div>
          ))}
        </div>

        {/* By-provider table */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.3 }}
        >
          <h2 className="text-sm font-semibold text-[var(--admin-text-secondary)] mb-3 uppercase tracking-wider">
            By Provider
          </h2>
          <div className="admin-card overflow-hidden">
            {loading ? (
              <div className="p-8 flex items-center justify-center">
                <div className="w-5 h-5 border-2 border-[var(--admin-primary)] border-t-transparent rounded-full animate-spin" />
              </div>
            ) : byProvider.length === 0 ? (
              <div className="p-8 text-center text-sm text-[var(--admin-text-muted)]">
                No provider usage data available
              </div>
            ) : (
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Provider</th>
                    <th>Requests</th>
                    <th>Cost</th>
                    <th>Share</th>
                    <th>Tokens</th>
                    <th>Avg Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {byProvider.map((row) => (
                    <tr key={row.provider_name}>
                      <td className="font-semibold text-[var(--admin-text-primary)]">
                        {row.provider_name}
                      </td>
                      <td>{formatNumber(row.request_count)}</td>
                      <td className="text-[var(--admin-accent)]">
                        {formatCost(row.total_cost_usd)}
                      </td>
                      <td>
                        {pct(
                          row.total_cost_usd,
                          summary?.total_cost_usd || 0
                        )}
                      </td>
                      <td>{formatNumber(row.total_tokens)}</td>
                      <td>{formatNumber(row.avg_latency_ms)}ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </motion.div>

        {/* By-service table */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.4 }}
        >
          <h2 className="text-sm font-semibold text-[var(--admin-text-secondary)] mb-3 uppercase tracking-wider">
            By Service
          </h2>
          <div className="admin-card overflow-hidden">
            {loading ? (
              <div className="p-8 flex items-center justify-center">
                <div className="w-5 h-5 border-2 border-[var(--admin-primary)] border-t-transparent rounded-full animate-spin" />
              </div>
            ) : byService.length === 0 ? (
              <div className="p-8 text-center text-sm text-[var(--admin-text-muted)]">
                No service usage data available
              </div>
            ) : (
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Service</th>
                    <th>Requests</th>
                    <th>Cost</th>
                    <th>Share</th>
                    <th>Tokens</th>
                  </tr>
                </thead>
                <tbody>
                  {byService.map((row) => (
                    <tr key={row.service_name}>
                      <td className="font-semibold text-[var(--admin-text-primary)]">
                        {row.service_name}
                      </td>
                      <td>{formatNumber(row.request_count)}</td>
                      <td className="text-[var(--admin-accent)]">
                        {formatCost(row.total_cost_usd)}
                      </td>
                      <td>
                        {pct(
                          row.total_cost_usd,
                          summary?.total_cost_usd || 0
                        )}
                      </td>
                      <td>{formatNumber(row.total_tokens)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </motion.div>
      </div>
    </AdminShell>
  );
}
