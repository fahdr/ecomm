/**
 * Settings page — profile information and navigation to related sections.
 *
 * Displays the user's profile (email, current plan) and provides
 * links to API Keys and Billing pages for quick access.
 *
 * **For Developers:**
 *   - User email is read from localStorage via `getUserEmail()`.
 *   - Plan info is fetched from `GET /api/v1/billing/overview`.
 *   - This page is intentionally lightweight — it serves as a hub to
 *     other settings-related pages rather than a dense configuration form.
 *   - Additional settings sections (notifications, integrations, etc.)
 *     should be added here as the service grows.
 *
 * **For Project Managers:**
 *   - Settings is a secondary page — keep it clean and focused.
 *   - Future additions: notification preferences, webhook URLs, team management.
 *
 * **For QA Engineers:**
 *   - Verify the correct email is displayed.
 *   - Verify the correct plan is displayed (matches billing page).
 *   - Test all navigation links lead to valid pages.
 *   - Verify loading states while plan data is being fetched.
 *
 * **For End Users:**
 *   - View your account information and plan details.
 *   - Quick links to manage API keys and billing.
 */

"use client";

import * as React from "react";
import Link from "next/link";
import { User, Key, CreditCard, ArrowUpRight } from "lucide-react";
import { Shell } from "@/components/shell";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { FadeIn, StaggerChildren, PageTransition } from "@/components/motion";
import { api } from "@/lib/api";
import { getUserEmail } from "@/lib/auth";
import { serviceConfig } from "@/service.config";

/** Shape of the billing overview response (subset needed for settings). */
interface BillingOverview {
  plan: string;
  status: string;
}

/**
 * Settings page component.
 *
 * @returns The settings page wrapped in the Shell layout.
 */
export default function SettingsPage() {
  const [email, setEmail] = React.useState<string | null>(null);
  const [plan, setPlan] = React.useState<BillingOverview | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    /* Read email from localStorage */
    setEmail(getUserEmail());

    /* Fetch plan information */
    async function fetchPlan() {
      const { data } = await api.get<BillingOverview>("/api/v1/billing/overview");
      if (data) setPlan(data);
      setLoading(false);
    }
    fetchPlan();
  }, []);

  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* ── Page Header ── */}
        <FadeIn direction="down">
          <div>
            <h2 className="font-heading text-2xl font-bold tracking-tight">
              Settings
            </h2>
            <p className="text-muted-foreground mt-1">
              Manage your account and preferences.
            </p>
          </div>
        </FadeIn>

        <StaggerChildren className="space-y-6" staggerDelay={0.1}>
          {/* ── Profile Section ── */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="size-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <User className="size-5 text-primary" />
                </div>
                <div>
                  <CardTitle>Profile</CardTitle>
                  <CardDescription>Your account information</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Email */}
              <div className="flex items-center justify-between py-3 border-b">
                <div>
                  <p className="text-sm font-medium">Email</p>
                  <p className="text-sm text-muted-foreground">
                    {email || "Not available"}
                  </p>
                </div>
              </div>

              {/* Current Plan */}
              <div className="flex items-center justify-between py-3">
                <div>
                  <p className="text-sm font-medium">Current Plan</p>
                  {loading ? (
                    <Skeleton className="h-4 w-24 mt-1" />
                  ) : (
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-sm text-muted-foreground capitalize">
                        {plan?.plan || "Free"}
                      </span>
                      <Badge
                        variant={plan?.status === "active" ? "success" : "secondary"}
                        className="text-xs"
                      >
                        {plan?.status || "active"}
                      </Badge>
                    </div>
                  )}
                </div>
                <Button asChild variant="outline" size="sm">
                  <Link href="/billing">
                    Manage
                    <ArrowUpRight className="size-3.5" />
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* ── Quick Links ── */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Links</CardTitle>
              <CardDescription>
                Navigate to commonly used settings
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* API Keys Link */}
              <Link
                href="/api-keys"
                className="flex items-center justify-between p-3 rounded-lg border hover:bg-secondary/50 transition-colors group"
              >
                <div className="flex items-center gap-3">
                  <div className="size-9 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Key className="size-4 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium">API Keys</p>
                    <p className="text-xs text-muted-foreground">
                      Create and manage your API keys
                    </p>
                  </div>
                </div>
                <ArrowUpRight className="size-4 text-muted-foreground group-hover:text-foreground transition-colors" />
              </Link>

              {/* Billing Link */}
              <Link
                href="/billing"
                className="flex items-center justify-between p-3 rounded-lg border hover:bg-secondary/50 transition-colors group"
              >
                <div className="flex items-center gap-3">
                  <div className="size-9 rounded-lg bg-primary/10 flex items-center justify-center">
                    <CreditCard className="size-4 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium">Billing</p>
                    <p className="text-xs text-muted-foreground">
                      Manage your subscription and view usage
                    </p>
                  </div>
                </div>
                <ArrowUpRight className="size-4 text-muted-foreground group-hover:text-foreground transition-colors" />
              </Link>
            </CardContent>
          </Card>

          {/* ── Service Info ── */}
          <Card>
            <CardHeader>
              <CardTitle>About</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <div className="size-10 rounded-lg bg-primary flex items-center justify-center">
                  <span className="text-primary-foreground font-bold font-heading">
                    {serviceConfig.name.charAt(0)}
                  </span>
                </div>
                <div>
                  <p className="font-heading font-bold">{serviceConfig.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {serviceConfig.tagline}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </StaggerChildren>
      </PageTransition>
    </Shell>
  );
}
