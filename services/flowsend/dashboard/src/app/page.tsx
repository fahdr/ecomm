/**
 * Dashboard home page — the main landing page after login.
 *
 * Fetches billing/usage overview data from the backend and displays
 * KPI cards with animated counters, quick action buttons, and a
 * welcome header branded with the service name.
 *
 * **For Developers:**
 *   - Fetches from `GET /api/v1/billing/overview` on mount.
 *   - Uses the `AnimatedCounter` component for smooth count-up effects on KPI values.
 *   - `StaggerChildren` provides a cascading reveal animation for the card grid.
 *   - Quick action buttons link to the most common workflows.
 *   - All data is optional — the page gracefully handles loading and error states.
 *
 * **For Project Managers:**
 *   - This is the first page users see after login — it should load fast.
 *   - KPI cards summarize the user's current plan, usage, and API activity.
 *   - Quick actions reduce clicks to the most common tasks.
 *
 * **For QA Engineers:**
 *   - Verify loading skeletons display before data arrives.
 *   - Test with API server down — should show error state, not crash.
 *   - Check animated counters count up smoothly to the correct values.
 *   - Verify KPI cards are responsive (grid collapses on mobile).
 *   - Test with zero usage data (new account) — should show 0, not blank.
 *
 * **For End Users:**
 *   - The dashboard shows your current usage and plan at a glance.
 *   - Click the quick action buttons to jump to common tasks.
 */

"use client";

import * as React from "react";
import Link from "next/link";
import { Activity, Key, CreditCard, ArrowUpRight } from "lucide-react";
import { Shell } from "@/components/shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { FadeIn, StaggerChildren, AnimatedCounter, PageTransition } from "@/components/motion";
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

/**
 * Dashboard home page component.
 *
 * @returns The dashboard home page wrapped in the Shell layout.
 */
export default function DashboardHomePage() {
  const [overview, setOverview] = React.useState<BillingOverview | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  /**
   * Fetch billing overview data on component mount.
   * Sets loading, data, and error states accordingly.
   */
  React.useEffect(() => {
    async function fetchOverview() {
      const { data, error: apiError } = await api.get<BillingOverview>(
        "/api/v1/billing/overview"
      );
      if (apiError) {
        setError(apiError.message);
      } else if (data) {
        setOverview(data);
      }
      setLoading(false);
    }
    fetchOverview();
  }, []);

  /** Calculate the usage percentage for the progress bar. */
  const usagePercent = overview
    ? overview.api_calls_limit > 0
      ? Math.round((overview.api_calls_used / overview.api_calls_limit) * 100)
      : 0
    : 0;

  /**
   * Determine the progress bar color based on usage percentage.
   * Green < 60%, Orange 60-85%, Red > 85%.
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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {Array.from({ length: 3 }).map((_, i) => (
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
                <p className="text-destructive text-sm">
                  Failed to load dashboard data: {error}
                </p>
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
          <StaggerChildren className="grid grid-cols-1 md:grid-cols-3 gap-6" staggerDelay={0.1}>
            {/* Card 1: Current Plan */}
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
                    {overview?.plan || "Free"}
                  </span>
                  <Badge
                    variant={overview?.status === "active" ? "success" : "secondary"}
                  >
                    {overview?.status || "active"}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  {overview?.billing_period_end
                    ? `Renews ${new Date(overview.billing_period_end).toLocaleDateString()}`
                    : "No active billing period"}
                </p>
              </CardContent>
            </Card>

            {/* Card 2: API Calls Used */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  API Calls Used
                </CardTitle>
                <Activity className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="flex items-baseline gap-1">
                  <AnimatedCounter
                    value={overview?.api_calls_used || 0}
                    formatter={(v) => v.toLocaleString()}
                    className="text-3xl font-bold font-heading"
                  />
                  <span className="text-sm text-muted-foreground">
                    / {(overview?.api_calls_limit || 0).toLocaleString()}
                  </span>
                </div>
                {/* Usage progress bar */}
                <div className="mt-3 h-2 rounded-full bg-secondary overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-700 ease-out ${getUsageColor(usagePercent)}`}
                    style={{ width: `${Math.min(usagePercent, 100)}%` }}
                  />
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {usagePercent}% of monthly limit
                </p>
              </CardContent>
            </Card>

            {/* Card 3: API Keys */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  API Keys
                </CardTitle>
                <Key className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold font-heading">
                  Manage
                </p>
                <p className="text-xs text-muted-foreground mt-2">
                  Create and manage your API keys for integration.
                </p>
                <Button asChild variant="outline" size="sm" className="mt-3">
                  <Link href="/api-keys">
                    View Keys
                    <ArrowUpRight className="size-3.5" />
                  </Link>
                </Button>
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
                <Link href="/api-keys">
                  <Key className="size-4" />
                  Create API Key
                </Link>
              </Button>
              <Button asChild variant="outline">
                <Link href="/billing">
                  <CreditCard className="size-4" />
                  Manage Billing
                </Link>
              </Button>
              <Button asChild variant="outline">
                <Link href="/settings">
                  <Activity className="size-4" />
                  View Settings
                </Link>
              </Button>
            </div>
          </div>
        </FadeIn>
      </PageTransition>
    </Shell>
  );
}
