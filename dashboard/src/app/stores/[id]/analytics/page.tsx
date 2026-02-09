/**
 * Analytics and profit dashboard page for a store.
 *
 * Displays revenue and profit charts using recharts, key financial
 * summary cards, and a ranked list of top-performing products. Data
 * is fetched from multiple analytics endpoints and composed into a
 * single cohesive view.
 *
 * **For End Users:**
 *   Track your store's financial performance at a glance. The revenue
 *   chart shows trends over time, summary cards highlight key metrics
 *   (revenue, profit, orders, avg order value), and the top products
 *   table shows what's selling best.
 *
 * **For QA Engineers:**
 *   - Summary data loads from ``GET /api/v1/stores/{store_id}/analytics/summary``.
 *   - Revenue chart data from ``GET /api/v1/stores/{store_id}/analytics/revenue``.
 *   - Top products from ``GET /api/v1/stores/{store_id}/analytics/top-products``.
 *   - Charts use the recharts library with responsive containers.
 *   - Period selector changes the time range (7d, 30d, 90d).
 *
 * **For Developers:**
 *   - Uses `useStore()` from the store context for the store ID.
 *   - Wrapped in `<PageTransition>` for consistent page entrance animations.
 *   - Three parallel API calls on mount (summary, revenue, top products).
 *   - Recharts components are imported from the ``recharts`` package.
 *   - The chart uses CSS variable colors via ``var(--chart-N)`` tokens.
 *
 * **For Project Managers:**
 *   Implements Feature 13 (Profit Analytics) from the backlog. Covers
 *   the core dashboard view; drill-down and export features are planned
 *   for a follow-up iteration.
 */

"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import { PageTransition } from "@/components/motion-wrappers";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from "recharts";

/** Summary metrics returned by the analytics summary endpoint. */
interface AnalyticsSummary {
  total_revenue: number | string;
  total_profit: number | string;
  total_orders: number;
  average_order_value: number | string;
  profit_margin: number;
  refund_total: number | string;
}

/** A single data point in the revenue time-series chart. */
interface RevenueDataPoint {
  date: string;
  revenue: number | string;
  cost: number | string;
  profit: number | string;
  orders: number;
}

/** A top-selling product from the analytics endpoint. */
interface TopProduct {
  product_id: string;
  product_title: string;
  revenue: number | string;
  cost: number | string;
  profit: number | string;
  units_sold: number;
  margin: number;
}

/**
 * Format a number as USD currency.
 * @param value - Numeric value to format.
 * @returns Formatted string like "$1,234.56".
 */
function formatCurrency(value: number | string): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Number(value));
}

/**
 * Analytics page component.
 *
 * Renders summary metric cards, a revenue/profit area chart, and a
 * top products table with period selection.
 *
 * @returns The analytics page wrapped in a PageTransition.
 */
export default function AnalyticsPage() {
  const { store } = useStore();
  const storeId = store?.id ?? "";
  const { user, loading: authLoading } = useAuth();

  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [revenueData, setRevenueData] = useState<RevenueDataPoint[]>([]);
  const [topProducts, setTopProducts] = useState<TopProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState("30d");

  /**
   * Fetch all analytics data in parallel.
   * @param selectedPeriod - The time period to fetch (7d, 30d, 90d).
   */
  const fetchAnalytics = useCallback(
    async (selectedPeriod: string) => {
      setLoading(true);
      setError(null);

      const [summaryResult, revenueResult, productsResult] = await Promise.all([
        api.get<AnalyticsSummary>(
          `/api/v1/stores/${storeId}/analytics/summary?period=${selectedPeriod}`
        ),
        api.get<RevenueDataPoint[]>(
          `/api/v1/stores/${storeId}/analytics/revenue?period=${selectedPeriod}`
        ),
        api.get<TopProduct[]>(
          `/api/v1/stores/${storeId}/analytics/top-products?period=${selectedPeriod}`
        ),
      ]);

      if (summaryResult.data) setSummary(summaryResult.data);
      if (revenueResult.data) {
        // API returns { period, data: [...] } wrapper
        const raw = revenueResult.data as any;
        setRevenueData(Array.isArray(raw) ? raw : raw.data ?? []);
      }
      if (productsResult.data) {
        // API returns { period, products: [...] } wrapper
        const raw = productsResult.data as any;
        setTopProducts(Array.isArray(raw) ? raw : raw.products ?? []);
      }

      if (summaryResult.error || revenueResult.error || productsResult.error) {
        setError("Some analytics data failed to load. Showing partial results.");
      }

      setLoading(false);
    },
    [storeId]
  );

  useEffect(() => {
    if (authLoading || !user || !storeId) return;
    fetchAnalytics(period);
  }, [storeId, user, authLoading, period, fetchAnalytics]);

  /**
   * Handle period change from the selector dropdown.
   * @param newPeriod - The selected time period string.
   */
  function handlePeriodChange(newPeriod: string) {
    setPeriod(newPeriod);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-foreground/20 border-t-foreground" />
          <p className="text-sm text-muted-foreground tracking-wide">Loading analytics...</p>
        </div>
      </div>
    );
  }

  return (
    <PageTransition>
      <main className="mx-auto max-w-4xl p-6 space-y-6">
        {/* Page heading with period selector */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-heading font-bold">Analytics</h1>
          <Select value={period} onValueChange={handlePeriodChange}>
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
              <SelectItem value="90d">Last 90 days</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {error && (
          <Card className="border-amber-300/50 bg-amber-50/50">
            <CardContent className="pt-6">
              <p className="text-sm text-amber-800">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* Summary metric cards */}
        {summary && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Revenue
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold tabular-nums">
                  {formatCurrency(summary.total_revenue)}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {summary.profit_margin.toFixed(1)}% margin
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Profit
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold tabular-nums text-emerald-600">
                  {formatCurrency(summary.total_profit)}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Refunds: {formatCurrency(summary.refund_total)}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Orders
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold tabular-nums">
                  {summary.total_orders.toLocaleString()}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {formatCurrency(summary.average_order_value)} avg
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Avg Order Value
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold tabular-nums">
                  {formatCurrency(summary.average_order_value)}
                </p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Revenue & profit chart */}
        <Card>
          <CardHeader>
            <CardTitle>Revenue & Profit Over Time</CardTitle>
            <CardDescription>
              Daily breakdown for the selected period
            </CardDescription>
          </CardHeader>
          <CardContent>
            {revenueData.length === 0 ? (
              <div className="flex h-64 items-center justify-center text-muted-foreground">
                No revenue data available for this period.
              </div>
            ) : (
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={revenueData}
                    margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient id="gradRevenue" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--chart-1)" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="var(--chart-1)" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="gradProfit" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--chart-2)" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="var(--chart-2)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 12 }}
                      className="fill-muted-foreground"
                      tickFormatter={(val: string) => {
                        const d = new Date(val);
                        return `${d.getMonth() + 1}/${d.getDate()}`;
                      }}
                    />
                    <YAxis
                      tick={{ fontSize: 12 }}
                      className="fill-muted-foreground"
                      tickFormatter={(val: number) =>
                        val >= 1000 ? `$${(val / 1000).toFixed(0)}k` : `$${val}`
                      }
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "var(--popover)",
                        border: "1px solid var(--border)",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      formatter={((value: any, name: any) => [
                        formatCurrency(Number(value) || 0),
                        String(name ?? "").charAt(0).toUpperCase() + String(name ?? "").slice(1),
                      ]) as any}
                      labelFormatter={((label: any) =>
                        new Date(String(label)).toLocaleDateString("en-US", {
                          weekday: "short",
                          month: "short",
                          day: "numeric",
                        })
                      ) as any}
                    />
                    <Area
                      type="monotone"
                      dataKey="revenue"
                      stroke="var(--chart-1)"
                      fill="url(#gradRevenue)"
                      strokeWidth={2}
                    />
                    <Area
                      type="monotone"
                      dataKey="profit"
                      stroke="var(--chart-2)"
                      fill="url(#gradProfit)"
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Top products table */}
        <Card>
          <CardHeader>
            <CardTitle>Top Products</CardTitle>
            <CardDescription>
              Best-performing products by revenue in the selected period
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {topProducts.length === 0 ? (
              <div className="flex h-32 items-center justify-center text-muted-foreground">
                No product sales data available for this period.
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="pl-6 w-10">#</TableHead>
                    <TableHead>Product</TableHead>
                    <TableHead>Revenue</TableHead>
                    <TableHead>Profit</TableHead>
                    <TableHead>Units Sold</TableHead>
                    <TableHead className="pr-6">Margin</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {topProducts.map((product, index) => (
                    <TableRow key={product.product_id}>
                      <TableCell className="pl-6 font-semibold text-muted-foreground tabular-nums">
                        {index + 1}
                      </TableCell>
                      <TableCell>
                        <Link
                          href={`/stores/${storeId}/products/${product.product_id}`}
                          className="font-medium hover:underline"
                        >
                          {product.product_title}
                        </Link>
                      </TableCell>
                      <TableCell className="font-semibold tabular-nums">
                        {formatCurrency(product.revenue)}
                      </TableCell>
                      <TableCell className="tabular-nums text-emerald-600">
                        {formatCurrency(product.profit)}
                      </TableCell>
                      <TableCell className="tabular-nums">
                        {product.units_sold.toLocaleString()}
                      </TableCell>
                      <TableCell className="pr-6">
                        <Badge
                          variant={product.margin >= 30 ? "default" : "secondary"}
                        >
                          {product.margin.toFixed(1)}%
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </main>
    </PageTransition>
  );
}
