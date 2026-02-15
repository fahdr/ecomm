/**
 * Analytics page — performance metrics and campaign analytics dashboard.
 *
 * Displays aggregated KPI cards (spend, revenue, ROAS, CTR, CPA, conversions),
 * a date-range filter, and per-campaign performance breakdowns in a table.
 *
 * **For Developers:**
 *   - Fetches from `GET /api/v1/metrics/overview` for aggregated KPIs.
 *   - Fetches from `GET /api/v1/campaigns` to list campaigns for per-campaign metrics.
 *   - Fetches from `GET /api/v1/metrics/campaign/{id}` for each campaign's daily data.
 *   - Date range filters use query parameters `start_date` and `end_date`.
 *   - Uses Shell wrapper, motion animations, AnimatedCounter for KPI numbers.
 *
 * **For Project Managers:**
 *   - This page is the main analytics dashboard for ad performance tracking.
 *   - ROAS (Return on Ad Spend) is the key metric for campaign profitability.
 *   - Fast, accurate metric aggregation is critical for user experience.
 *
 * **For QA Engineers:**
 *   - Test loading skeleton display before data arrives.
 *   - Test with no campaigns (empty state with zero KPIs).
 *   - Test date range filter changes trigger data refresh.
 *   - Verify KPI calculations match expected values (ROAS = revenue/spend).
 *   - Test animated counters count up to correct values.
 *   - Test responsive layout (card grid, table scroll).
 *
 * **For End Users:**
 *   - Track your ad performance at a glance with KPI cards.
 *   - Use the date filter to analyze performance over custom time periods.
 *   - View per-campaign breakdowns to identify your best and worst performers.
 */

"use client";

import * as React from "react";
import {
  BarChart3,
  DollarSign,
  TrendingUp,
  MousePointerClick,
  Eye,
  ShoppingCart,
  Target,
  Calendar,
  RefreshCw,
} from "lucide-react";
import { Shell } from "@/components/shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { FadeIn, StaggerChildren, AnimatedCounter, PageTransition } from "@/components/motion";
import { api } from "@/lib/api";

/* ── Types ──────────────────────────────────────────────────────────── */

/** Aggregated metrics overview from the backend. */
interface MetricsOverview {
  total_spend: number;
  total_revenue: number;
  total_impressions: number;
  total_clicks: number;
  total_conversions: number;
  avg_roas: number | null;
  avg_ctr: number | null;
  avg_cpa: number | null;
}

/** Campaign shape for the performance table. */
interface Campaign {
  id: string;
  name: string;
  platform: string;
  objective: string;
  status: string;
  budget_daily: number | null;
  budget_lifetime: number | null;
}

/** Paginated campaigns response. */
interface CampaignsResponse {
  items: Campaign[];
  total: number;
  offset: number;
  limit: number;
}

/** Per-campaign daily metric record. */
interface CampaignMetric {
  id: string;
  campaign_id: string;
  date: string;
  impressions: number;
  clicks: number;
  conversions: number;
  spend: number;
  revenue: number;
  roas: number | null;
  cpa: number | null;
  ctr: number | null;
}

/** Paginated metrics response. */
interface MetricsResponse {
  items: CampaignMetric[];
  total: number;
  offset: number;
  limit: number;
}

/** Aggregated per-campaign summary computed client-side. */
interface CampaignSummary {
  campaign: Campaign;
  totalSpend: number;
  totalRevenue: number;
  totalImpressions: number;
  totalClicks: number;
  totalConversions: number;
  roas: number | null;
}

/* ── Helpers ────────────────────────────────────────────────────────── */

/**
 * Format a number as USD currency.
 *
 * @param value - The numeric value to format.
 * @returns A formatted currency string.
 */
function formatCurrency(value: number): string {
  return `$${value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

/**
 * Format a decimal as a percentage string.
 *
 * @param value - The decimal value (e.g. 3.5 for 3.5%).
 * @returns A formatted percentage string.
 */
function formatPercent(value: number | null): string {
  if (value === null || value === undefined) return "---";
  return `${value.toFixed(2)}%`;
}

/**
 * Get the default start date (30 days ago) in ISO format.
 *
 * @returns A YYYY-MM-DD string.
 */
function defaultStartDate(): string {
  const d = new Date();
  d.setDate(d.getDate() - 30);
  return d.toISOString().split("T")[0];
}

/**
 * Get today's date in ISO format.
 *
 * @returns A YYYY-MM-DD string.
 */
function defaultEndDate(): string {
  return new Date().toISOString().split("T")[0];
}

/** Status variant mapping for campaign badges. */
const STATUS_VARIANTS: Record<string, "success" | "default" | "secondary" | "destructive"> = {
  active: "success",
  draft: "secondary",
  paused: "default",
  completed: "destructive",
};

/* ── Component ──────────────────────────────────────────────────────── */

/**
 * Analytics dashboard page component.
 *
 * @returns The analytics page wrapped in the Shell layout with motion animations.
 */
export default function AnalyticsPage() {
  const [overview, setOverview] = React.useState<MetricsOverview | null>(null);
  const [campaigns, setCampaigns] = React.useState<Campaign[]>([]);
  const [campaignSummaries, setCampaignSummaries] = React.useState<CampaignSummary[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [startDate, setStartDate] = React.useState(defaultStartDate);
  const [endDate, setEndDate] = React.useState(defaultEndDate);

  /**
   * Fetch overview metrics and campaign list from the backend.
   * Then fetch per-campaign metrics for the performance table.
   */
  const fetchData = React.useCallback(async () => {
    setLoading(true);
    setError(null);

    const dateParams = `start_date=${startDate}&end_date=${endDate}`;

    const [overviewResult, campaignsResult] = await Promise.all([
      api.get<MetricsOverview>(`/api/v1/metrics/overview?${dateParams}`),
      api.get<CampaignsResponse>("/api/v1/campaigns?limit=100"),
    ]);

    if (overviewResult.error) {
      setError(overviewResult.error.message);
      setLoading(false);
      return;
    }

    if (overviewResult.data) {
      setOverview(overviewResult.data);
    }

    const campList = campaignsResult.data?.items || [];
    setCampaigns(campList);

    /* Fetch per-campaign metrics for the breakdown table */
    if (campList.length > 0) {
      const metricPromises = campList.map((c) =>
        api.get<MetricsResponse>(
          `/api/v1/metrics/campaign/${c.id}?${dateParams}&limit=365`
        )
      );
      const metricResults = await Promise.all(metricPromises);

      const summaries: CampaignSummary[] = campList.map((campaign, idx) => {
        const metrics = metricResults[idx].data?.items || [];
        const totalSpend = metrics.reduce((sum, m) => sum + m.spend, 0);
        const totalRevenue = metrics.reduce((sum, m) => sum + m.revenue, 0);
        const totalImpressions = metrics.reduce((sum, m) => sum + m.impressions, 0);
        const totalClicks = metrics.reduce((sum, m) => sum + m.clicks, 0);
        const totalConversions = metrics.reduce((sum, m) => sum + m.conversions, 0);

        return {
          campaign,
          totalSpend,
          totalRevenue,
          totalImpressions,
          totalClicks,
          totalConversions,
          roas: totalSpend > 0 ? totalRevenue / totalSpend : null,
        };
      });

      /* Sort by spend descending */
      summaries.sort((a, b) => b.totalSpend - a.totalSpend);
      setCampaignSummaries(summaries);
    } else {
      setCampaignSummaries([]);
    }

    setLoading(false);
  }, [startDate, endDate]);

  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* ── Header ── */}
        <FadeIn direction="down">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight flex items-center gap-2">
                <BarChart3 className="size-6" />
                Analytics
              </h2>
              <p className="text-muted-foreground mt-1">
                Track performance metrics across all your campaigns.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1.5">
                <Calendar className="size-4 text-muted-foreground" />
                <Input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-36 text-xs"
                />
                <span className="text-muted-foreground text-xs">to</span>
                <Input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-36 text-xs"
                />
              </div>
              <Button variant="outline" size="sm" onClick={fetchData} disabled={loading}>
                <RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} />
              </Button>
            </div>
          </div>
        </FadeIn>

        {/* ── KPI Cards ── */}
        {loading ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Card key={i}>
                <CardHeader className="pb-2">
                  <Skeleton className="h-3 w-16" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-7 w-20" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : error ? (
          <FadeIn>
            <Card className="border-destructive/50">
              <CardContent className="pt-6">
                <p className="text-destructive text-sm">
                  Failed to load analytics: {error}
                </p>
                <Button variant="outline" size="sm" className="mt-3" onClick={fetchData}>
                  Retry
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        ) : (
          <StaggerChildren
            className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4"
            staggerDelay={0.06}
          >
            {/* Total Spend */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">
                  Total Spend
                </CardTitle>
                <DollarSign className="size-3.5 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <AnimatedCounter
                  value={overview?.total_spend || 0}
                  formatter={(v) => formatCurrency(v)}
                  className="text-xl font-bold font-heading"
                />
              </CardContent>
            </Card>

            {/* Total Revenue */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">
                  Revenue
                </CardTitle>
                <TrendingUp className="size-3.5 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <AnimatedCounter
                  value={overview?.total_revenue || 0}
                  formatter={(v) => formatCurrency(v)}
                  className="text-xl font-bold font-heading"
                />
              </CardContent>
            </Card>

            {/* ROAS */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">
                  Avg ROAS
                </CardTitle>
                <Target className="size-3.5 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <p className="text-xl font-bold font-heading">
                  {overview?.avg_roas !== null && overview?.avg_roas !== undefined
                    ? `${overview.avg_roas.toFixed(2)}x`
                    : "---"}
                </p>
              </CardContent>
            </Card>

            {/* Impressions */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">
                  Impressions
                </CardTitle>
                <Eye className="size-3.5 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <AnimatedCounter
                  value={overview?.total_impressions || 0}
                  formatter={(v) => v.toLocaleString()}
                  className="text-xl font-bold font-heading"
                />
              </CardContent>
            </Card>

            {/* Clicks / CTR */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">
                  Clicks (CTR)
                </CardTitle>
                <MousePointerClick className="size-3.5 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="flex items-baseline gap-1.5">
                  <AnimatedCounter
                    value={overview?.total_clicks || 0}
                    formatter={(v) => v.toLocaleString()}
                    className="text-xl font-bold font-heading"
                  />
                  <span className="text-xs text-muted-foreground">
                    ({formatPercent(overview?.avg_ctr ?? null)})
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* Conversions / CPA */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">
                  Conv. (CPA)
                </CardTitle>
                <ShoppingCart className="size-3.5 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="flex items-baseline gap-1.5">
                  <AnimatedCounter
                    value={overview?.total_conversions || 0}
                    formatter={(v) => v.toLocaleString()}
                    className="text-xl font-bold font-heading"
                  />
                  <span className="text-xs text-muted-foreground">
                    ({overview?.avg_cpa !== null && overview?.avg_cpa !== undefined
                      ? formatCurrency(overview.avg_cpa)
                      : "---"})
                  </span>
                </div>
              </CardContent>
            </Card>
          </StaggerChildren>
        )}

        {/* ── Campaign Performance Table ── */}
        {!loading && !error && (
          <FadeIn delay={0.3}>
            <div>
              <h3 className="font-heading text-lg font-semibold mb-4">
                Campaign Performance
              </h3>
              {campaignSummaries.length === 0 ? (
                <Card>
                  <CardContent className="pt-6 text-center py-12">
                    <BarChart3 className="size-10 mx-auto text-muted-foreground mb-3" />
                    <p className="text-muted-foreground text-sm">
                      No campaign data for the selected date range.
                    </p>
                  </CardContent>
                </Card>
              ) : (
                <Card className="overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b bg-secondary/30">
                          <th className="text-left py-3 px-4 font-medium text-muted-foreground">
                            Campaign
                          </th>
                          <th className="text-left py-3 px-4 font-medium text-muted-foreground">
                            Status
                          </th>
                          <th className="text-right py-3 px-4 font-medium text-muted-foreground">
                            Spend
                          </th>
                          <th className="text-right py-3 px-4 font-medium text-muted-foreground">
                            Revenue
                          </th>
                          <th className="text-right py-3 px-4 font-medium text-muted-foreground">
                            ROAS
                          </th>
                          <th className="text-right py-3 px-4 font-medium text-muted-foreground">
                            Impressions
                          </th>
                          <th className="text-right py-3 px-4 font-medium text-muted-foreground">
                            Clicks
                          </th>
                          <th className="text-right py-3 px-4 font-medium text-muted-foreground">
                            Conv.
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {campaignSummaries.map((s) => (
                          <tr
                            key={s.campaign.id}
                            className="border-b last:border-0 hover:bg-secondary/20 transition-colors"
                          >
                            <td className="py-3 px-4">
                              <div>
                                <p className="font-medium truncate max-w-[200px]">
                                  {s.campaign.name}
                                </p>
                                <p className="text-xs text-muted-foreground capitalize">
                                  {s.campaign.platform} &middot; {s.campaign.objective}
                                </p>
                              </div>
                            </td>
                            <td className="py-3 px-4">
                              <Badge
                                variant={STATUS_VARIANTS[s.campaign.status] || "secondary"}
                              >
                                {s.campaign.status}
                              </Badge>
                            </td>
                            <td className="py-3 px-4 text-right font-mono text-xs">
                              {formatCurrency(s.totalSpend)}
                            </td>
                            <td className="py-3 px-4 text-right font-mono text-xs">
                              {formatCurrency(s.totalRevenue)}
                            </td>
                            <td className="py-3 px-4 text-right font-mono text-xs">
                              {s.roas !== null ? (
                                <span
                                  className={
                                    s.roas >= 2
                                      ? "text-emerald-600 dark:text-emerald-400"
                                      : s.roas >= 1
                                      ? "text-amber-600 dark:text-amber-400"
                                      : "text-destructive"
                                  }
                                >
                                  {s.roas.toFixed(2)}x
                                </span>
                              ) : (
                                "---"
                              )}
                            </td>
                            <td className="py-3 px-4 text-right font-mono text-xs">
                              {s.totalImpressions.toLocaleString()}
                            </td>
                            <td className="py-3 px-4 text-right font-mono text-xs">
                              {s.totalClicks.toLocaleString()}
                            </td>
                            <td className="py-3 px-4 text-right font-mono text-xs">
                              {s.totalConversions.toLocaleString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                      {/* Totals row */}
                      <tfoot>
                        <tr className="bg-secondary/20 font-semibold">
                          <td className="py-3 px-4" colSpan={2}>
                            Total ({campaignSummaries.length} campaign{campaignSummaries.length !== 1 ? "s" : ""})
                          </td>
                          <td className="py-3 px-4 text-right font-mono text-xs">
                            {formatCurrency(
                              campaignSummaries.reduce((s, c) => s + c.totalSpend, 0)
                            )}
                          </td>
                          <td className="py-3 px-4 text-right font-mono text-xs">
                            {formatCurrency(
                              campaignSummaries.reduce((s, c) => s + c.totalRevenue, 0)
                            )}
                          </td>
                          <td className="py-3 px-4 text-right font-mono text-xs">
                            {(() => {
                              const totalSpend = campaignSummaries.reduce(
                                (s, c) => s + c.totalSpend,
                                0
                              );
                              const totalRevenue = campaignSummaries.reduce(
                                (s, c) => s + c.totalRevenue,
                                0
                              );
                              return totalSpend > 0
                                ? `${(totalRevenue / totalSpend).toFixed(2)}x`
                                : "---";
                            })()}
                          </td>
                          <td className="py-3 px-4 text-right font-mono text-xs">
                            {campaignSummaries
                              .reduce((s, c) => s + c.totalImpressions, 0)
                              .toLocaleString()}
                          </td>
                          <td className="py-3 px-4 text-right font-mono text-xs">
                            {campaignSummaries
                              .reduce((s, c) => s + c.totalClicks, 0)
                              .toLocaleString()}
                          </td>
                          <td className="py-3 px-4 text-right font-mono text-xs">
                            {campaignSummaries
                              .reduce((s, c) => s + c.totalConversions, 0)
                              .toLocaleString()}
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </Card>
              )}
            </div>
          </FadeIn>
        )}

        {/* ── Date Range Info ── */}
        {!loading && !error && (
          <FadeIn delay={0.4}>
            <p className="text-xs text-muted-foreground text-center">
              Showing data from {new Date(startDate).toLocaleDateString()} to{" "}
              {new Date(endDate).toLocaleDateString()}
            </p>
          </FadeIn>
        )}
      </PageTransition>
    </Shell>
  );
}
