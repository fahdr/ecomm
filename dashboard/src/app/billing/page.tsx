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
 */
function formatLimit(value: number): string {
  return value === -1 ? "Unlimited" : value.toLocaleString();
}

/**
 * Calculate usage percentage for a progress bar.
 * Returns 0 for unlimited limits (-1).
 */
function usagePercent(used: number, limit: number): number {
  if (limit === -1) return 0;
  if (limit === 0) return 100;
  return Math.min(Math.round((used / limit) * 100), 100);
}

/**
 * Format a date string to a human-readable format.
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
 * Outer wrapper that provides the required Suspense boundary for
 * `useSearchParams()` (required by Next.js App Router for static generation).
 */
export default function BillingPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <p className="text-muted-foreground">Loading...</p>
        </div>
      }
    >
      <BillingContent />
    </Suspense>
  );
}

/** Inner billing page component that uses search params and auth context. */
function BillingContent() {
  const { user, loading: authLoading, logout } = useAuth();
  const searchParams = useSearchParams();
  const [billing, setBilling] = useState<BillingOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [portalLoading, setPortalLoading] = useState(false);

  const showSuccess = searchParams.get("success") === "true";

  useEffect(() => {
    if (authLoading || !user) return;

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

  if (loading || authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  if (!billing) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Failed to load billing data.</p>
      </div>
    );
  }

  const isFree = billing.current_plan === "free";

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b px-6 py-4">
        <div className="flex items-center gap-6">
          <h1 className="text-lg font-semibold">Dropshipping Dashboard</h1>
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
          <span className="text-sm text-muted-foreground">{user?.email}</span>
          <Button variant="outline" size="sm" onClick={logout}>
            Log out
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-3xl space-y-6 px-6 py-12">
        {showSuccess && (
          <div className="rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
            Your subscription has been activated. Welcome aboard!
          </div>
        )}

        <h2 className="text-3xl font-bold tracking-tight">Billing</h2>

        {/* Current Plan Card */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Current Plan</CardTitle>
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
            <CardTitle>Usage</CardTitle>
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
      </main>
    </div>
  );
}

/**
 * A single usage metric row with label, count, and progress bar.
 *
 * @param label - The metric name.
 * @param used - Current usage count.
 * @param limit - Plan limit (-1 for unlimited).
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
