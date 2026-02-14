/**
 * Billing page — plan management, usage metrics, and subscription controls.
 *
 * Displays the user's current plan, usage metrics with visual progress bars,
 * a comparison of all available plans, and buttons to upgrade or manage
 * the subscription via Stripe portal.
 *
 * **For Developers:**
 *   - Fetches from `GET /api/v1/billing/overview` for current plan + usage.
 *   - `POST /api/v1/billing/checkout` initiates a Stripe Checkout session (returns `{ url }`).
 *   - `POST /api/v1/billing/portal` opens the Stripe Customer Portal (returns `{ url }`).
 *   - Plan tiers are defined in `serviceConfig.plans` — no hardcoded plans here.
 *   - Progress bars color-code by percentage: green < 60%, orange 60-85%, red > 85%.
 *
 * **For Project Managers:**
 *   - This page drives revenue — the upgrade flow should be smooth and compelling.
 *   - Plan comparison cards highlight the value proposition of each tier.
 *   - Usage bars create urgency for users approaching their limits.
 *
 * **For QA Engineers:**
 *   - Test with each plan tier (free, pro, enterprise) — verify correct display.
 *   - Test upgrade button — should redirect to Stripe Checkout.
 *   - Test manage button — should redirect to Stripe Customer Portal.
 *   - Verify progress bars render correctly at 0%, 50%, 75%, 95%, and 100%.
 *   - Test with API errors — should show error state.
 *   - Verify the "Current Plan" badge appears on the active plan card.
 *
 * **For End Users:**
 *   - View your current plan and usage at the top of the page.
 *   - Compare plans to find the right fit for your needs.
 *   - Click "Upgrade" to switch to a higher plan.
 *   - Click "Manage Subscription" to update payment or cancel.
 */

"use client";

import * as React from "react";
import { CreditCard, ArrowUpRight, Loader2, Check, Zap } from "lucide-react";
import { Shell } from "@/components/shell";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { FadeIn, StaggerChildren, AnimatedCounter, PageTransition } from "@/components/motion";
import { api } from "@/lib/api";
import { serviceConfig } from "@/service.config";
import { cn } from "@/lib/utils";

/** Shape of the billing overview response. */
interface BillingOverview {
  plan: string;
  status: string;
  api_calls_used: number;
  api_calls_limit: number;
  billing_period_end: string;
}

/**
 * Determine progress bar color class based on usage percentage.
 *
 * @param percent - Usage percentage (0-100).
 * @returns A Tailwind background color class.
 */
function getBarColor(percent: number): string {
  if (percent < 60) return "bg-emerald-500";
  if (percent < 85) return "bg-amber-500";
  return "bg-red-500";
}

/**
 * Billing page component.
 *
 * @returns The billing page wrapped in the Shell layout.
 */
export default function BillingPage() {
  const [overview, setOverview] = React.useState<BillingOverview | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [checkoutLoading, setCheckoutLoading] = React.useState<string | null>(null);
  const [portalLoading, setPortalLoading] = React.useState(false);

  /** Fetch billing overview on mount. */
  React.useEffect(() => {
    async function fetchBilling() {
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
    fetchBilling();
  }, []);

  /**
   * Initiate a Stripe Checkout session for upgrading to a plan.
   *
   * @param tier - The plan tier to upgrade to (e.g. "pro", "enterprise").
   */
  async function handleUpgrade(tier: string) {
    setCheckoutLoading(tier);
    const { data, error: apiError } = await api.post<{ url: string }>(
      "/api/v1/billing/checkout",
      { tier }
    );
    setCheckoutLoading(null);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    if (data?.url) {
      window.location.href = data.url;
    }
  }

  /**
   * Open the Stripe Customer Portal for managing the subscription.
   */
  async function handleManageSubscription() {
    setPortalLoading(true);
    const { data, error: apiError } = await api.post<{ url: string }>(
      "/api/v1/billing/portal",
      {}
    );
    setPortalLoading(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    if (data?.url) {
      window.location.href = data.url;
    }
  }

  /** Calculate usage percentage. */
  const usagePercent = overview
    ? overview.api_calls_limit > 0
      ? Math.round((overview.api_calls_used / overview.api_calls_limit) * 100)
      : 0
    : 0;

  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* ── Page Header ── */}
        <FadeIn direction="down">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight">
                Billing & Usage
              </h2>
              <p className="text-muted-foreground mt-1">
                Manage your subscription and monitor API usage.
              </p>
            </div>
            {overview && overview.plan !== "free" && (
              <Button
                variant="outline"
                onClick={handleManageSubscription}
                disabled={portalLoading}
              >
                {portalLoading && <Loader2 className="size-4 animate-spin" />}
                <CreditCard className="size-4" />
                Manage Subscription
              </Button>
            )}
          </div>
        </FadeIn>

        {/* ── Current Plan & Usage ── */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader><Skeleton className="h-4 w-24" /></CardHeader>
              <CardContent className="space-y-3">
                <Skeleton className="h-8 w-32" />
                <Skeleton className="h-3 w-full" />
              </CardContent>
            </Card>
            <Card>
              <CardHeader><Skeleton className="h-4 w-24" /></CardHeader>
              <CardContent className="space-y-3">
                <Skeleton className="h-8 w-32" />
                <Skeleton className="h-3 w-full" />
              </CardContent>
            </Card>
          </div>
        ) : error && !overview ? (
          <FadeIn>
            <Card className="border-destructive/50">
              <CardContent className="pt-6">
                <p className="text-destructive text-sm">
                  Failed to load billing data: {error}
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
          <StaggerChildren className="grid grid-cols-1 md:grid-cols-2 gap-6" staggerDelay={0.1}>
            {/* Current Plan Card */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Current Plan
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-3">
                  <span className="text-3xl font-bold font-heading capitalize">
                    {overview?.plan || "Free"}
                  </span>
                  <Badge
                    variant={overview?.status === "active" ? "success" : "secondary"}
                  >
                    {overview?.status || "active"}
                  </Badge>
                </div>
                {overview?.billing_period_end && (
                  <p className="text-sm text-muted-foreground mt-2">
                    Current period ends{" "}
                    {new Date(overview.billing_period_end).toLocaleDateString(undefined, {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                    })}
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Usage Metrics Card */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  API Usage This Period
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-baseline gap-1">
                  <AnimatedCounter
                    value={overview?.api_calls_used || 0}
                    formatter={(v) => v.toLocaleString()}
                    className="text-3xl font-bold font-heading"
                  />
                  <span className="text-sm text-muted-foreground">
                    / {(overview?.api_calls_limit || 0).toLocaleString()} calls
                  </span>
                </div>
                {/* Progress bar */}
                <div className="mt-4 space-y-2">
                  <div className="h-3 rounded-full bg-secondary overflow-hidden">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all duration-1000 ease-out",
                        getBarColor(usagePercent)
                      )}
                      style={{ width: `${Math.min(usagePercent, 100)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>{usagePercent}% used</span>
                    <span>
                      {((overview?.api_calls_limit || 0) - (overview?.api_calls_used || 0)).toLocaleString()} remaining
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </StaggerChildren>
        )}

        {/* ── Plan Comparison Cards ── */}
        <FadeIn delay={0.3}>
          <div>
            <h3 className="font-heading text-lg font-semibold mb-4">
              Available Plans
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {serviceConfig.plans.map((plan) => {
                const isCurrentPlan = overview?.plan?.toLowerCase() === plan.tier;
                const isPopular = plan.tier === "pro";

                return (
                  <Card
                    key={plan.tier}
                    className={cn(
                      "relative overflow-hidden transition-shadow hover:shadow-md",
                      isPopular && "border-primary shadow-md",
                      isCurrentPlan && "ring-2 ring-primary"
                    )}
                  >
                    {/* Popular badge */}
                    {isPopular && (
                      <div className="absolute top-0 right-0 bg-primary text-primary-foreground text-xs font-bold px-3 py-1 rounded-bl-lg">
                        Popular
                      </div>
                    )}

                    <CardHeader>
                      <CardTitle className="font-heading text-xl">
                        {plan.name}
                      </CardTitle>
                      <CardDescription>
                        <span className="text-3xl font-bold text-foreground font-heading">
                          ${plan.price}
                        </span>
                        <span className="text-muted-foreground">/month</span>
                      </CardDescription>
                    </CardHeader>

                    <CardContent className="space-y-3">
                      {plan.features.length > 0 ? (
                        plan.features.map((feature, i) => (
                          <div key={i} className="flex items-start gap-2">
                            <Check className="size-4 text-primary shrink-0 mt-0.5" />
                            <span className="text-sm">{feature}</span>
                          </div>
                        ))
                      ) : (
                        <p className="text-sm text-muted-foreground italic">
                          Features not yet configured
                        </p>
                      )}
                    </CardContent>

                    <CardFooter>
                      {isCurrentPlan ? (
                        <Badge variant="outline" className="w-full justify-center py-2">
                          Current Plan
                        </Badge>
                      ) : (
                        <Button
                          className="w-full"
                          variant={isPopular ? "default" : "outline"}
                          onClick={() => handleUpgrade(plan.tier)}
                          disabled={checkoutLoading === plan.tier}
                        >
                          {checkoutLoading === plan.tier ? (
                            <Loader2 className="size-4 animate-spin" />
                          ) : (
                            <Zap className="size-4" />
                          )}
                          {plan.price === 0 ? "Get Started" : "Upgrade"}
                          <ArrowUpRight className="size-3.5" />
                        </Button>
                      )}
                    </CardFooter>
                  </Card>
                );
              })}
            </div>
          </div>
        </FadeIn>

        {/* ── Error Toast (inline) ── */}
        {error && overview && (
          <FadeIn>
            <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          </FadeIn>
        )}
      </PageTransition>
    </Shell>
  );
}
