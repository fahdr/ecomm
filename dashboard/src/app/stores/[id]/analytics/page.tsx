/**
 * Analytics and profit dashboard page for a store.
 *
 * Displays revenue and profit charts using recharts, key financial
 * summary cards, customer metrics, and a ranked list of top-performing
 * products. Data is fetched from multiple analytics endpoints and
 * composed into a single cohesive view.
 *
 * **For End Users:**
 *   Track your store's financial performance at a glance. The revenue
 *   chart shows trends over time, summary cards highlight key metrics
 *   (revenue, profit, orders, avg order value), and the top products
 *   table shows what's selling best. Customer metrics help you understand
 *   your buyer base.
 *
 * **For QA Engineers:**
 *   - Summary data loads from ``GET /api/v1/stores/{store_id}/analytics/summary``.
 *   - Revenue chart data from ``GET /api/v1/stores/{store_id}/analytics/revenue``.
 *   - Top products from ``GET /api/v1/stores/{store_id}/analytics/top-products``.
 *   - Customer count from ``GET /api/v1/stores/{store_id}/customers``.
 *   - Charts use the recharts library with responsive containers.
 *   - Period selector changes the time range (7d, 30d, 90d).
 *   - Metric cards animate with count-up effect on load.
 *
 * **For Developers:**
 *   - Uses `useStore()` from the store context for the store ID.
 *   - Wrapped in `<PageTransition>` for consistent page entrance animations.
 *   - Three+ parallel API calls on mount (summary, revenue, top products, customers).
 *   - Recharts components are imported from the ``recharts`` package.
 *   - The chart uses CSS variable colors via ``var(--chart-N)`` tokens.
 *   - AnimatedNumber component provides count-up effect on metric cards.
 *
 * **For Project Managers:**
 *   Implements Feature 13 (Profit Analytics) from the backlog. Now includes
 *   customer metrics and order status breakdown for a comprehensive view.
 *
 * @module app/stores/[id]/analytics/page
 */

"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import { PageTransition, FadeIn } from "@/components/motion-wrappers";
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
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
} from "recharts";
import {
  DollarSign,
  TrendingUp,
  ShoppingCart,
  Users,
  Repeat,
  UserPlus,
} from "lucide-react";

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

/** Customer metrics derived from the customers endpoint. */
interface CustomerMetrics {
  totalCustomers: number;
  avgOrdersPerCustomer: number;
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
 * Animated number component — counts up from 0 to target value.
 *
 * @param props - Component props.
 * @param props.value - Target number to animate to.
 * @param props.prefix - Optional prefix string (e.g. "$").
 * @param props.suffix - Optional suffix string (e.g. "%").
 * @param props.decimals - Number of decimal places.
 * @param props.duration - Animation duration in ms.
 * @returns A span with the animated number value.
 */
function AnimatedNumber({
  value,
  prefix = "",
  suffix = "",
  decimals = 0,
  duration = 1200,
}: {
  value: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  duration?: number;
}) {
  const [display, setDisplay] = useState(0);
  const frameRef = useRef<number>(0);

  useEffect(() => {
    const start = performance.now();
    const from = 0;

    function tick(now: number) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic.
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(from + (value - from) * eased);
      if (progress < 1) {
        frameRef.current = requestAnimationFrame(tick);
      }
    }

    frameRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameRef.current);
  }, [value, duration]);

  const formatted = decimals > 0
    ? display.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
    : Math.round(display).toLocaleString();

  return (
    <span>
      {prefix}{formatted}{suffix}
    </span>
  );
}

/**
 * Analytics page component.
 *
 * Renders summary metric cards with animated counters, a revenue/profit
 * area chart, customer metrics, order status breakdown, and a top
 * products table with period selection.
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
  const [customerMetrics, setCustomerMetrics] = useState<CustomerMetrics | null>(null);
  const [orderStatusBreakdown, setOrderStatusBreakdown] = useState<{ status: string; count: number }[]>([]);
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

      const [summaryResult, revenueResult, productsResult, customersResult] = await Promise.all([
        api.get<AnalyticsSummary>(
          `/api/v1/stores/${storeId}/analytics/summary?period=${selectedPeriod}`
        ),
        api.get<RevenueDataPoint[]>(
          `/api/v1/stores/${storeId}/analytics/revenue?period=${selectedPeriod}`
        ),
        api.get<TopProduct[]>(
          `/api/v1/stores/${storeId}/analytics/top-products?period=${selectedPeriod}`
        ),
        api.get<{ items: { id: string; total_orders: number }[]; total: number }>(
          `/api/v1/stores/${storeId}/customers?per_page=100`
        ),
      ]);

      if (summaryResult.data) setSummary(summaryResult.data);
      if (revenueResult.data) {
        const raw = revenueResult.data as any;
        setRevenueData(Array.isArray(raw) ? raw : raw.data ?? []);
      }
      if (productsResult.data) {
        const raw = productsResult.data as any;
        setTopProducts(Array.isArray(raw) ? raw : raw.products ?? []);
      }

      // Derive customer metrics.
      if (customersResult.data) {
        const raw = customersResult.data as any;
        const items = Array.isArray(raw) ? raw : raw.items ?? [];
        const total = raw.total ?? items.length;
        const totalOrdersAll = items.reduce((sum: number, c: any) => sum + (c.total_orders || 0), 0);
        setCustomerMetrics({
          totalCustomers: total,
          avgOrdersPerCustomer: total > 0 ? totalOrdersAll / total : 0,
        });
      }

      // Derive order status breakdown from revenue data (orders per day) and summary.
      // We'll fetch a small batch of orders to get status counts.
      const ordersRes = await api.get<any>(
        `/api/v1/stores/${storeId}/orders?per_page=200`
      );
      if (ordersRes.data) {
        const orders = Array.isArray(ordersRes.data) ? ordersRes.data : ordersRes.data.items ?? [];
        const statusMap: Record<string, number> = {};
        for (const o of orders) {
          const s = o.status || "unknown";
          statusMap[s] = (statusMap[s] || 0) + 1;
        }
        setOrderStatusBreakdown(
          Object.entries(statusMap)
            .map(([status, count]) => ({ status, count }))
            .sort((a, b) => b.count - a.count)
        );
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

  /** Status colors for the order breakdown chart. */
  const statusColors: Record<string, string> = {
    pending: "var(--chart-3)",
    processing: "var(--chart-1)",
    shipped: "var(--chart-2)",
    delivered: "var(--chart-4)",
    completed: "var(--chart-2)",
    cancelled: "var(--chart-5)",
    refunded: "var(--chart-5)",
  };

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

        {/* Summary metric cards — animated counters */}
        {summary && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardContent className="pt-5 pb-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Revenue</p>
                    <p className="text-2xl font-bold tabular-nums mt-1">
                      <AnimatedNumber value={Number(summary.total_revenue)} prefix="$" />
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {summary.profit_margin.toFixed(1)}% margin
                    </p>
                  </div>
                  <div className="p-2 rounded-lg text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30">
                    <DollarSign className="h-4 w-4" />
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-5 pb-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Profit</p>
                    <p className="text-2xl font-bold tabular-nums text-emerald-600 mt-1">
                      <AnimatedNumber value={Number(summary.total_profit)} prefix="$" />
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Refunds: {formatCurrency(summary.refund_total)}
                    </p>
                  </div>
                  <div className="p-2 rounded-lg text-blue-600 bg-blue-100 dark:bg-blue-900/30">
                    <TrendingUp className="h-4 w-4" />
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-5 pb-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Orders</p>
                    <p className="text-2xl font-bold tabular-nums mt-1">
                      <AnimatedNumber value={summary.total_orders} />
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {formatCurrency(summary.average_order_value)} avg
                    </p>
                  </div>
                  <div className="p-2 rounded-lg text-purple-600 bg-purple-100 dark:bg-purple-900/30">
                    <ShoppingCart className="h-4 w-4" />
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-5 pb-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Avg Order</p>
                    <p className="text-2xl font-bold tabular-nums mt-1">
                      <AnimatedNumber value={Number(summary.average_order_value)} prefix="$" decimals={2} />
                    </p>
                  </div>
                  <div className="p-2 rounded-lg text-amber-600 bg-amber-100 dark:bg-amber-900/30">
                    <DollarSign className="h-4 w-4" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Customer Metrics */}
        {customerMetrics && (
          <FadeIn delay={0.1}>
            <div className="grid gap-4 sm:grid-cols-3">
              <Card>
                <CardContent className="pt-5 pb-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg text-indigo-600 bg-indigo-100 dark:bg-indigo-900/30">
                      <Users className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Total Customers</p>
                      <p className="text-xl font-bold tabular-nums">
                        <AnimatedNumber value={customerMetrics.totalCustomers} />
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-5 pb-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg text-teal-600 bg-teal-100 dark:bg-teal-900/30">
                      <Repeat className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Avg Orders/Customer</p>
                      <p className="text-xl font-bold tabular-nums">
                        <AnimatedNumber value={customerMetrics.avgOrdersPerCustomer} decimals={1} />
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-5 pb-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg text-rose-600 bg-rose-100 dark:bg-rose-900/30">
                      <UserPlus className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Repeat Rate</p>
                      <p className="text-xl font-bold tabular-nums">
                        <AnimatedNumber
                          value={customerMetrics.totalCustomers > 0 && customerMetrics.avgOrdersPerCustomer > 1
                            ? ((customerMetrics.avgOrdersPerCustomer - 1) / customerMetrics.avgOrdersPerCustomer) * 100
                            : 0}
                          suffix="%"
                          decimals={1}
                        />
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </FadeIn>
        )}

        {/* Revenue & profit chart */}
        <FadeIn delay={0.15}>
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
        </FadeIn>

        {/* Order Status Breakdown */}
        {orderStatusBreakdown.length > 0 && (
          <FadeIn delay={0.2}>
            <Card>
              <CardHeader>
                <CardTitle>Order Status Breakdown</CardTitle>
                <CardDescription>
                  Distribution of orders by current status
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={orderStatusBreakdown}
                      margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                      <XAxis
                        dataKey="status"
                        tick={{ fontSize: 12 }}
                        className="fill-muted-foreground"
                        tickFormatter={(v: string) => v.charAt(0).toUpperCase() + v.slice(1)}
                      />
                      <YAxis tick={{ fontSize: 12 }} className="fill-muted-foreground" />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "var(--popover)",
                          border: "1px solid var(--border)",
                          borderRadius: "8px",
                          fontSize: "12px",
                        }}
                        // eslint-disable-next-line @typescript-eslint/no-explicit-any
                        formatter={((value: any) => [value, "Orders"]) as any}
                        labelFormatter={(label: any) =>
                          String(label).charAt(0).toUpperCase() + String(label).slice(1)
                        }
                      />
                      <Bar
                        dataKey="count"
                        radius={[4, 4, 0, 0]}
                        fill="var(--chart-1)"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </FadeIn>
        )}

        {/* Top products table */}
        <FadeIn delay={0.25}>
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
        </FadeIn>
      </main>
    </PageTransition>
  );
}
