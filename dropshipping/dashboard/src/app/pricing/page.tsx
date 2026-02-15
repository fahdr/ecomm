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
 *   - Renders inside the unified dashboard shell (sidebar + top bar).
 *
 * **For Developers:**
 *   - Wrapped in `AuthenticatedLayout` for the unified shell.
 *   - Main content wrapped in `PageTransition` for entrance animation.
 *
 * **For Project Managers:**
 *   This page is part of the top-level dashboard (not store-scoped).
 *   It displays subscription tiers and handles Stripe checkout flow.
 */

"use client";

import { useEffect, useState } from "react";
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
import { PageTransition } from "@/components/motion-wrappers";
import { AuthenticatedLayout } from "@/components/authenticated-layout";

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
 * PricingPage displays all available subscription plans and handles checkout.
 *
 * @returns The rendered pricing page inside the unified shell.
 */
export default function PricingPage() {
  const { user, loading: authLoading } = useAuth();
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

  const currentPlan = user?.plan || "free";

  return (
    <AuthenticatedLayout>
      <div className="mx-auto max-w-5xl px-6 py-12">
        <PageTransition>
          {loading || authLoading ? (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="h-64 rounded-xl border bg-muted/30 animate-pulse"
                />
              ))}
            </div>
          ) : (
            <>
              <div className="mb-8 text-center">
                <h2 className="text-3xl font-heading font-bold tracking-tight">
                  Choose your plan
                </h2>
                <p className="mt-2 text-muted-foreground">
                  Start free and scale as your business grows. All paid plans
                  include a 14-day free trial.
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
                          <CardTitle className="font-heading">
                            {plan.name}
                          </CardTitle>
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
                          disabled={
                            isCurrent || isFree || subscribing !== null
                          }
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
            </>
          )}
        </PageTransition>
      </div>
    </AuthenticatedLayout>
  );
}
