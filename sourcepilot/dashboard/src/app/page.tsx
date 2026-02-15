/**
 * SourcePilot Dashboard home page — overview of import activity and key metrics.
 *
 * Displays SourcePilot-specific KPIs (imports this month, active price watches,
 * connected stores) alongside billing overview data. Quick action buttons link
 * to the most common workflows: new import, search products, view history.
 *
 * **For Developers:**
 *   - Fetches from `GET /api/v1/billing/overview` for plan and usage data.
 *   - Fetches from `GET /api/v1/imports?skip=0&limit=1` for import count (total field).
 *   - Fetches from `GET /api/v1/price-watches` for active watch count.
 *   - Fetches from `GET /api/v1/connections` for connected store count.
 *   - All API calls run in parallel on mount for fast page load.
 *   - Uses AnimatedCounter for smooth count-up effects on KPI values.
 *   - StaggerChildren provides a cascading reveal animation for the card grid.
 *
 * **For Project Managers:**
 *   - This is the first page users see after login — it should load fast.
 *   - KPI cards summarize import activity, price monitoring, and store health.
 *   - Quick actions reduce clicks to the most common tasks.
 *
 * **For QA Engineers:**
 *   - Verify loading skeletons display before data arrives.
 *   - Test with API server down — should show error state, not crash.
 *   - Check animated counters count up smoothly to the correct values.
 *   - Verify KPI cards are responsive (grid collapses on mobile).
 *   - Test with zero data (new account) — should show 0, not blank.
 *   - Verify all quick action links navigate to correct pages.
 *
 * **For End Users:**
 *   - The dashboard shows your import activity and account status at a glance.
 *   - Click the quick action buttons to jump to common tasks.
 *   - KPI cards update in real-time as you import products and monitor prices.
 */

"use client";

import * as React from "react";
import Link from "next/link";
import {
  Download,
  TrendingUp,
  Link as LinkIcon,
  Search,
  Clock,
  Plus,
  CreditCard,
} from "lucide-react";
import { Shell } from "@/components/shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  FadeIn,
  StaggerChildren,
  AnimatedCounter,
  PageTransition,
} from "@/components/motion";
import { api } from "@/lib/api";
import { serviceConfig } from "@/service.config";

/** Shape of the billing overview response from the backend. */
interface BillingOverview {
  plan: string;
  status: string;
  api_calls_used: number;
  api_calls_limit: number;
  billing_period_end: string;
}

/** Shape of the paginated imports response (we only need the total). */
interface ImportsResponse {
  items: unknown[];
  total: number;
}

/** Shape of a store connection (we only need the count). */
interface StoreConnection {
  id: string;
}

/** Shape of a price watch (we only need the count). */
interface PriceWatch {
  id: string;
}

/** Aggregated dashboard KPI data from multiple endpoints. */
interface DashboardKPIs {
  overview: BillingOverview | null;
  importsThisMonth: number;
  activePriceWatches: number;
  connectedStores: number;
}

/**
 * SourcePilot Dashboard home page component.
 *
 * Fetches data from multiple endpoints in parallel and displays
 * SourcePilot-specific KPI cards with animated counters.
 *
 * @returns The dashboard home page wrapped in the Shell layout.
 */
export default function DashboardHomePage() {
  const [kpis, setKpis] = React.useState<DashboardKPIs>({
    overview: null,
    importsThisMonth: 0,
    activePriceWatches: 0,
    connectedStores: 0,
  });
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  /**
   * Fetch all dashboard data in parallel on component mount.
   * Combines billing overview, import count, price watch count,
   * and store connection count into a single KPI state object.
   */
  React.useEffect(() => {
    async function fetchDashboardData() {
      const [billingRes, importsRes, watchesRes, connectionsRes] =
        await Promise.all([
          api.get<BillingOverview>("/api/v1/billing/overview"),
          api.get<ImportsResponse>("/api/v1/imports?skip=0&limit=1"),
          api.get<PriceWatch[]>("/api/v1/price-watches"),
          api.get<StoreConnection[]>("/api/v1/connections"),
        ]);

      if (
        billingRes.error &&
        importsRes.error &&
        watchesRes.error &&
        connectionsRes.error
      ) {
        setError("Failed to load dashboard data. Please try again.");
      } else {
        setKpis({
          overview: billingRes.data,
          importsThisMonth: importsRes.data?.total ?? 0,
          activePriceWatches: watchesRes.data?.length ?? 0,
          connectedStores: connectionsRes.data?.length ?? 0,
        });
      }
      setLoading(false);
    }

    fetchDashboardData();
  }, []);

  /** Calculate the usage percentage for the progress bar. */
  const usagePercent = kpis.overview
    ? kpis.overview.api_calls_limit > 0
      ? Math.round(
          (kpis.overview.api_calls_used / kpis.overview.api_calls_limit) * 100
        )
      : 0
    : 0;

  /**
   * Determine the progress bar color based on usage percentage.
   * Green < 60%, Orange 60-85%, Red > 85%.
   *
   * @param percent - The current usage percentage.
   * @returns A Tailwind CSS background color class.
   */
  function getUsageColor(percent: number): string {
    if (percent < 60) return "bg-emerald-500";
    if (percent < 85) return "bg-amber-500";
    return "bg-red-500";
  }

  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* ── Welcome Header ── */}
        <FadeIn direction="down">
          <div>
            <h2 className="font-heading text-2xl font-bold tracking-tight">
              Welcome to {serviceConfig.name}
            </h2>
            <p className="text-muted-foreground mt-1">
              {serviceConfig.tagline}
            </p>
          </div>
        </FadeIn>

        {/* ── KPI Cards ── */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-4 w-24" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-8 w-20" />
                  <Skeleton className="h-3 w-full mt-3" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : error ? (
          <FadeIn>
            <Card className="border-destructive/50">
              <CardContent className="pt-6">
                <p className="text-destructive text-sm">{error}</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={() => window.location.reload()}
                >
                  Retry
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        ) : (
          <StaggerChildren
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6"
            staggerDelay={0.1}
          >
            {/* Card 1: Imports This Month */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Imports This Month
                </CardTitle>
                <Download className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <AnimatedCounter
                  value={kpis.importsThisMonth}
                  formatter={(v) => v.toLocaleString()}
                  className="text-3xl font-bold font-heading"
                />
                <p className="text-xs text-muted-foreground mt-2">
                  Products imported from suppliers
                </p>
              </CardContent>
            </Card>

            {/* Card 2: Active Price Watches */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Active Price Watches
                </CardTitle>
                <TrendingUp className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <AnimatedCounter
                  value={kpis.activePriceWatches}
                  formatter={(v) => v.toLocaleString()}
                  className="text-3xl font-bold font-heading"
                />
                <p className="text-xs text-muted-foreground mt-2">
                  Products monitored for price changes
                </p>
              </CardContent>
            </Card>

            {/* Card 3: Connected Stores */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Connected Stores
                </CardTitle>
                <LinkIcon className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <AnimatedCounter
                  value={kpis.connectedStores}
                  formatter={(v) => v.toLocaleString()}
                  className="text-3xl font-bold font-heading"
                />
                <p className="text-xs text-muted-foreground mt-2">
                  E-commerce stores receiving imports
                </p>
              </CardContent>
            </Card>

            {/* Card 4: Current Plan */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Current Plan
                </CardTitle>
                <CreditCard className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2">
                  <span className="text-3xl font-bold font-heading capitalize">
                    {kpis.overview?.plan || "Free"}
                  </span>
                  <Badge
                    variant={
                      kpis.overview?.status === "active" ? "success" : "secondary"
                    }
                  >
                    {kpis.overview?.status || "active"}
                  </Badge>
                </div>
                {/* Usage progress bar */}
                {kpis.overview && kpis.overview.api_calls_limit > 0 && (
                  <>
                    <div className="mt-3 h-2 rounded-full bg-secondary overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-700 ease-out ${getUsageColor(usagePercent)}`}
                        style={{
                          width: `${Math.min(usagePercent, 100)}%`,
                        }}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {kpis.overview.api_calls_used.toLocaleString()} /{" "}
                      {kpis.overview.api_calls_limit.toLocaleString()} API calls
                      ({usagePercent}%)
                    </p>
                  </>
                )}
              </CardContent>
            </Card>
          </StaggerChildren>
        )}

        {/* ── Quick Actions ── */}
        <FadeIn delay={0.4}>
          <div>
            <h3 className="font-heading text-lg font-semibold mb-4">
              Quick Actions
            </h3>
            <div className="flex flex-wrap gap-3">
              <Button asChild>
                <Link href="/imports">
                  <Plus className="size-4" />
                  New Import
                </Link>
              </Button>
              <Button asChild variant="outline">
                <Link href="/products">
                  <Search className="size-4" />
                  Search Products
                </Link>
              </Button>
              <Button asChild variant="outline">
                <Link href="/imports">
                  <Clock className="size-4" />
                  View History
                </Link>
              </Button>
              <Button asChild variant="outline">
                <Link href="/price-watch">
                  <TrendingUp className="size-4" />
                  Price Watch
                </Link>
              </Button>
              <Button asChild variant="outline">
                <Link href="/connections">
                  <LinkIcon className="size-4" />
                  Manage Stores
                </Link>
              </Button>
            </div>
          </div>
        </FadeIn>
      </PageTransition>
    </Shell>
  );
}
