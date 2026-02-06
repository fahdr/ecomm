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
 */
function formatLimit(value: number): string {
  return value === -1 ? "Unlimited" : value.toLocaleString();
}

/**
 * Format cents to a dollar string.
 * Returns "$0" for free, otherwise "$XX/mo".
 */
function formatPrice(cents: number): string {
  if (cents === 0) return "$0";
  return `$${(cents / 100).toFixed(0)}/mo`;
}

export default function PricingPage() {
  const { user, loading: authLoading, logout } = useAuth();
  const [plans, setPlans] = useState<PlanInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [subscribing, setSubscribing] = useState<string | null>(null);

  useEffect(() => {
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

  if (loading || authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  const currentPlan = user?.plan || "free";

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
          <span className="text-sm text-muted-foreground">{user?.email}</span>
          <Button variant="outline" size="sm" onClick={logout}>
            Log out
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-12">
        <div className="mb-8 text-center">
          <h2 className="text-3xl font-bold tracking-tight">Choose your plan</h2>
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
                    <CardTitle>{plan.name}</CardTitle>
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
      </main>
    </div>
  );
}
