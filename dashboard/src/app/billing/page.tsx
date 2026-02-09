/**
 * Billing page.
 *
 * Shows the user's current plan, subscription status, and resource usage.
 * Provides links to the Stripe Customer Portal for managing subscriptions
 * and to the pricing page for upgrading.
 *
 * **For End Users:**
 *   View your current plan details, see how many stores and products
 *   you're using, and manage your subscription.
 *
 * **For QA Engineers:**
 *   - Fetches data from `GET /api/v1/subscriptions/billing` (auth required).
 *   - Free-tier users see an upgrade CTA instead of "Manage Subscription".
 *   - "Manage Subscription" calls `POST /api/v1/subscriptions/portal` and
 *     redirects to the returned `portal_url`.
 *   - Usage bars show stores, products, and orders against plan limits.
 *   - `?success=true` query param shows a success banner after checkout.
 *   - Loading state uses Skeleton placeholders instead of text spinners.
 *
 * **For Developers:**
 *   - Uses `bg-dot-pattern` background for visual consistency with the overhaul.
 *   - Header uses backdrop blur and `font-heading` for titles.
 *   - Main content wrapped in `PageTransition` for entrance animation.
 *   - ThemeToggle is present in the header for dark/light mode switching.
 *   - Suspense boundary wraps inner content for `useSearchParams()`.
 *
 * **For Project Managers:**
 *   This page is part of the top-level dashboard (not store-scoped).
 *   It allows users to view and manage their subscription billing.
 */

"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PageTransition } from "@/components/motion-wrappers";
import { ThemeToggle } from "@/components/theme-toggle";

/** Subscription data from the billing API. */
interface Subscription {
  id: string;
  plan: string;
  status: string;
  current_period_start: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
  trial_start: string | null;
  trial_end: string | null;
}

/** Usage data from the billing API. */
interface Usage {
  stores_used: number;
  stores_limit: number;
  products_used: number;
  products_limit_per_store: number;
  orders_this_month: number;
  orders_limit: number;
}

/** Billing overview response from the API. */
interface BillingOverview {
  current_plan: string;
  plan_name: string;
  subscription: Subscription | null;
  usage: Usage;
}

/** Portal session response from the API. */
interface PortalResponse {
  portal_url: string;
}

/**
 * Format a limit for display.
 * Returns "Unlimited" for -1, otherwise the number.
 *
 * @param value - The numeric limit value.
 * @returns A human-readable limit string.
 */
function formatLimit(value: number): string {
  return value === -1 ? "Unlimited" : value.toLocaleString();
}

/**
 * Calculate usage percentage for a progress bar.
 * Returns 0 for unlimited limits (-1).
 *
 * @param used - Current usage count.
 * @param limit - Plan limit (-1 for unlimited).
 * @returns The percentage used, capped at 100.
 */
function usagePercent(used: number, limit: number): number {
  if (limit === -1) return 0;
  if (limit === 0) return 100;
  return Math.min(Math.round((used / limit) * 100), 100);
}

/**
 * Format a date string to a human-readable format.
 *
 * @param dateStr - ISO date string from the API.
 * @returns A formatted date string like "January 1, 2025".
 */
function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

/**
 * Get a display variant for the subscription status badge.
 *
 * @param status - The subscription status string.
 * @returns The appropriate Badge variant for visual styling.
 */
function statusVariant(
  status: string
): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "active":
      return "default";
    case "trialing":
      return "secondary";
    case "past_due":
      return "destructive";
    case "canceled":
      return "outline";
    default:
      return "outline";
  }
}

/**
 * Skeleton loading state for the billing page.
 *
 * Renders placeholder shapes that approximate the billing page layout
 * while data is being fetched.
 *
 * @returns Skeleton placeholders matching the billing page structure.
 */
function BillingSkeleton() {
  return (
    <div className="min-h-screen bg-dot-pattern">
      <header className="flex items-center justify-between border-b bg-background/80 backdrop-blur-sm px-6 py-4">
        <div className="flex items-center gap-6">
          <Skeleton className="h-6 w-48" />
          <div className="flex items-center gap-4">
            <Skeleton className="h-4 w-14" />
            <Skeleton className="h-4 w-14" />
            <Skeleton className="h-4 w-14" />
          </div>
        </div>
        <div className="flex items-center gap-4">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-8 w-16 rounded-md" />
        </div>
      </header>
      <main className="mx-auto max-w-3xl space-y-6 px-6 py-12">
        <Skeleton className="h-9 w-32" />
        <Card>
          <CardHeader>
            <Skeleton className="h-5 w-28" />
            <Skeleton className="h-4 w-48 mt-2" />
          </CardHeader>
          <CardContent className="space-y-4">
            <Skeleton className="h-4 w-64" />
            <Skeleton className="h-9 w-40 rounded-md" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <Skeleton className="h-5 w-16" />
            <Skeleton className="h-4 w-56 mt-2" />
          </CardHeader>
          <CardContent className="space-y-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="space-y-2">
                <div className="flex justify-between">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-4 w-16" />
                </div>
                <Skeleton className="h-2 w-full rounded-full" />
              </div>
            ))}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}

/**
 * Outer wrapper that provides the required Suspense boundary for
 * `useSearchParams()` (required by Next.js App Router for static generation).
 *
 * @returns The billing page wrapped in a Suspense boundary.
 */
export default function BillingPage() {
  return (
    <Suspense fallback={<BillingSkeleton />}>
      <BillingContent />
    </Suspense>
  );
}

/**
 * Inner billing page component that uses search params and auth context.
 *
 * Fetches billing data, displays current plan / subscription status,
 * and renders usage metrics with progress bars.
 *
 * @returns The fully rendered billing page content.
 */
function BillingContent() {
  const { user, loading: authLoading, logout } = useAuth();
  const searchParams = useSearchParams();
  const [billing, setBilling] = useState<BillingOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [portalLoading, setPortalLoading] = useState(false);

  const showSuccess = searchParams.get("success") === "true";

  useEffect(() => {
    if (authLoading || !user) return;

    /**
     * Fetch the billing overview from the subscriptions API.
     */
    async function fetchBilling() {
      const result = await api.get<BillingOverview>(
        "/api/v1/subscriptions/billing"
      );
      if (result.data) {
        setBilling(result.data);
      }
      setLoading(false);
    }
    fetchBilling();
  }, [authLoading, user]);

  /**
   * Open the Stripe Customer Portal for subscription management.
   * Posts to the portal endpoint and redirects to the returned URL.
   */
  async function handleManageSubscription() {
    setPortalLoading(true);
    const result = await api.post<PortalResponse>(
      "/api/v1/subscriptions/portal",
      {}
    );
    if (result.data) {
      window.location.href = result.data.portal_url;
    }
    setPortalLoading(false);
  }

  /* Show skeleton while data is loading. */
  if (loading || authLoading) {
    return <BillingSkeleton />;
  }

  /* Show error state if billing data failed to load. */
  if (!billing) {
    return (
      <div className="flex min-h-screen bg-dot-pattern items-center justify-center">
        <p className="text-muted-foreground">Failed to load billing data.</p>
      </div>
    );
  }

  const isFree = billing.current_plan === "free";

  return (
    <div className="min-h-screen bg-dot-pattern">
      <header className="flex items-center justify-between border-b bg-background/80 backdrop-blur-sm px-6 py-4">
        <div className="flex items-center gap-6">
          <h1 className="text-lg font-heading font-semibold">Dropshipping Dashboard</h1>
          <nav className="flex items-center gap-4">
            <Link
              href="/stores"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Stores
            </Link>
            <Link
              href="/billing"
              className="text-sm font-medium text-foreground transition-colors"
            >
              Billing
            </Link>
            <Link
              href="/pricing"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Pricing
            </Link>
          </nav>
        </div>
        <div className="flex items-center gap-4">
          <ThemeToggle />
          <span className="text-sm text-muted-foreground">{user?.email}</span>
          <Button variant="outline" size="sm" onClick={logout}>
            Log out
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-3xl space-y-6 px-6 py-12">
        <PageTransition>
          {showSuccess && (
            <div className="rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800 mb-6">
              Your subscription has been activated. Welcome aboard!
            </div>
          )}

          <h2 className="text-3xl font-heading font-bold tracking-tight">Billing</h2>

          {/* Current Plan Card */}
          <Card className="mt-6">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="font-heading">Current Plan</CardTitle>
                {billing.subscription && (
                  <Badge variant={statusVariant(billing.subscription.status)}>
                    {billing.subscription.status}
                  </Badge>
                )}
              </div>
              <CardDescription>
                You are on the <span className="font-medium">{billing.plan_name}</span> plan.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {billing.subscription && (
                <div className="text-sm text-muted-foreground space-y-1">
                  <p>
                    Current period:{" "}
                    {formatDate(billing.subscription.current_period_start)} &mdash;{" "}
                    {formatDate(billing.subscription.current_period_end)}
                  </p>
                  {billing.subscription.cancel_at_period_end && (
                    <p className="text-orange-600 font-medium">
                      Cancels at end of billing period
                    </p>
                  )}
                </div>
              )}
              <div className="flex gap-3">
                {isFree ? (
                  <Link href="/pricing">
                    <Button>Upgrade Plan</Button>
                  </Link>
                ) : (
                  <>
                    <Button
                      onClick={handleManageSubscription}
                      disabled={portalLoading}
                    >
                      {portalLoading ? "Loading..." : "Manage Subscription"}
                    </Button>
                    <Link href="/pricing">
                      <Button variant="outline">Change Plan</Button>
                    </Link>
                  </>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Usage Card */}
          <Card>
            <CardHeader>
              <CardTitle className="font-heading">Usage</CardTitle>
              <CardDescription>
                Your current resource usage against plan limits.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <UsageRow
                label="Stores"
                used={billing.usage.stores_used}
                limit={billing.usage.stores_limit}
              />
              <UsageRow
                label="Products per store"
                used={billing.usage.products_used}
                limit={billing.usage.products_limit_per_store}
              />
              <UsageRow
                label="Orders this month"
                used={billing.usage.orders_this_month}
                limit={billing.usage.orders_limit}
              />
            </CardContent>
          </Card>
        </PageTransition>
      </main>
    </div>
  );
}

/**
 * A single usage metric row with label, count, and progress bar.
 *
 * Renders a progress bar colored by proximity to the limit:
 * green (default primary) under 70%, orange at 70-89%, red at 90%+.
 * Unlimited limits (-1) show a minimal bar.
 *
 * @param label - The metric name (e.g. "Stores").
 * @param used - Current usage count.
 * @param limit - Plan limit (-1 for unlimited).
 * @returns A row with label, usage fraction, and colored progress bar.
 */
function UsageRow({
  label,
  used,
  limit,
}: {
  label: string;
  used: number;
  limit: number;
}) {
  const percent = usagePercent(used, limit);
  const isUnlimited = limit === -1;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className="text-muted-foreground">
          {used.toLocaleString()} / {formatLimit(limit)}
        </span>
      </div>
      <div className="h-2 rounded-full bg-muted">
        <div
          className={`h-2 rounded-full transition-all ${
            isUnlimited
              ? "bg-muted-foreground/20"
              : percent >= 90
                ? "bg-destructive"
                : percent >= 70
                  ? "bg-orange-500"
                  : "bg-primary"
          }`}
          style={{ width: isUnlimited ? "5%" : `${Math.max(percent, 2)}%` }}
        />
      </div>
    </div>
  );
}
