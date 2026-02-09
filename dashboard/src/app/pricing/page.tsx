/**
 * Pricing page.
 *
 * Displays all available subscription plans in a card grid. Users can
 * compare features and limits across tiers, and click "Subscribe" to
 * start a Stripe Checkout session.
 *
 * **For End Users:**
 *   Compare plans to find the best fit for your business. Click
 *   "Subscribe" on a paid plan to start your free trial.
 *
 * **For QA Engineers:**
 *   - Fetches plans from `GET /api/v1/subscriptions/plans` (no auth required).
 *   - The current plan shows "Current Plan" badge and disabled button.
 *   - Subscribe button calls `POST /api/v1/subscriptions/checkout` and
 *     redirects to the returned `checkout_url`.
 *   - Free plan button is always disabled.
 *   - Loading state uses Skeleton placeholders instead of text spinners.
 *
 * **For Developers:**
 *   - Uses `bg-dot-pattern` background for visual consistency with the overhaul.
 *   - Header uses backdrop blur and `font-heading` for titles.
 *   - Main content wrapped in `PageTransition` for entrance animation.
 *   - ThemeToggle is present in the header for dark/light mode switching.
 *
 * **For Project Managers:**
 *   This page is part of the top-level dashboard (not store-scoped).
 *   It displays subscription tiers and handles Stripe checkout flow.
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
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

/** Plan information returned by the API. */
interface PlanInfo {
  tier: string;
  name: string;
  price_monthly_cents: number;
  max_stores: number;
  max_products_per_store: number;
  max_orders_per_month: number;
  trial_days: number;
}

/** Checkout session response from the API. */
interface CheckoutResponse {
  checkout_url: string;
  session_id: string;
}

/**
 * Format a limit value for display.
 * Returns "Unlimited" for -1, otherwise the number.
 *
 * @param value - The numeric limit value.
 * @returns A human-readable limit string.
 */
function formatLimit(value: number): string {
  return value === -1 ? "Unlimited" : value.toLocaleString();
}

/**
 * Format cents to a dollar string.
 * Returns "$0" for free, otherwise "$XX/mo".
 *
 * @param cents - Price in cents.
 * @returns A formatted price string.
 */
function formatPrice(cents: number): string {
  if (cents === 0) return "$0";
  return `$${(cents / 100).toFixed(0)}/mo`;
}

/**
 * Skeleton loading state for the pricing page.
 *
 * Renders placeholder shapes that approximate the pricing page layout
 * while plan data is being fetched.
 *
 * @returns Skeleton placeholders matching the pricing page structure.
 */
function PricingSkeleton() {
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
      <main className="mx-auto max-w-5xl px-6 py-12">
        <div className="mb-8 text-center">
          <Skeleton className="h-9 w-64 mx-auto" />
          <Skeleton className="h-4 w-96 mx-auto mt-3" />
        </div>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-24" />
                <Skeleton className="h-7 w-20 mt-2" />
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                </div>
                <Skeleton className="h-9 w-full rounded-md" />
              </CardContent>
            </Card>
          ))}
        </div>
      </main>
    </div>
  );
}

/**
 * PricingPage displays all available subscription plans and handles checkout.
 *
 * Fetches plan data from the API, renders a comparison grid, and
 * creates Stripe checkout sessions when users subscribe.
 *
 * @returns The rendered pricing page with header and plan cards.
 */
export default function PricingPage() {
  const { user, loading: authLoading, logout } = useAuth();
  const [plans, setPlans] = useState<PlanInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [subscribing, setSubscribing] = useState<string | null>(null);

  useEffect(() => {
    /**
     * Fetch available subscription plans from the API.
     */
    async function fetchPlans() {
      const result = await api.get<PlanInfo[]>("/api/v1/subscriptions/plans");
      if (result.data) {
        setPlans(result.data);
      }
      setLoading(false);
    }
    fetchPlans();
  }, []);

  /**
   * Handle subscribe button click.
   * Creates a checkout session and redirects to Stripe.
   *
   * @param tier - The plan tier to subscribe to.
   */
  async function handleSubscribe(tier: string) {
    setSubscribing(tier);
    const result = await api.post<CheckoutResponse>(
      "/api/v1/subscriptions/checkout",
      { plan: tier }
    );
    if (result.data) {
      window.location.href = result.data.checkout_url;
    }
    setSubscribing(null);
  }

  /* Show skeleton while data is loading. */
  if (loading || authLoading) {
    return <PricingSkeleton />;
  }

  const currentPlan = user?.plan || "free";

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
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Billing
            </Link>
            <Link
              href="/pricing"
              className="text-sm font-medium text-foreground transition-colors"
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

      <main className="mx-auto max-w-5xl px-6 py-12">
        <PageTransition>
          <div className="mb-8 text-center">
            <h2 className="text-3xl font-heading font-bold tracking-tight">Choose your plan</h2>
            <p className="mt-2 text-muted-foreground">
              Start free and scale as your business grows. All paid plans include a
              14-day free trial.
            </p>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {plans.map((plan) => {
              const isCurrent = plan.tier === currentPlan;
              const isFree = plan.tier === "free";

              return (
                <Card
                  key={plan.tier}
                  className={isCurrent ? "border-primary" : ""}
                >
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="font-heading">{plan.name}</CardTitle>
                      {isCurrent && <Badge>Current Plan</Badge>}
                    </div>
                    <CardDescription className="text-2xl font-bold text-foreground">
                      {formatPrice(plan.price_monthly_cents)}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <ul className="space-y-2 text-sm">
                      <li>
                        <span className="font-medium">
                          {formatLimit(plan.max_stores)}
                        </span>{" "}
                        {plan.max_stores === 1 ? "store" : "stores"}
                      </li>
                      <li>
                        <span className="font-medium">
                          {formatLimit(plan.max_products_per_store)}
                        </span>{" "}
                        products per store
                      </li>
                      <li>
                        <span className="font-medium">
                          {formatLimit(plan.max_orders_per_month)}
                        </span>{" "}
                        orders/month
                      </li>
                      {plan.trial_days > 0 && (
                        <li className="text-muted-foreground">
                          {plan.trial_days}-day free trial
                        </li>
                      )}
                    </ul>
                    <Button
                      className="w-full"
                      disabled={isCurrent || isFree || subscribing !== null}
                      onClick={() => handleSubscribe(plan.tier)}
                    >
                      {subscribing === plan.tier
                        ? "Redirecting..."
                        : isCurrent
                          ? "Current Plan"
                          : isFree
                            ? "Free"
                            : "Subscribe"}
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </PageTransition>
      </main>
    </div>
  );
}
