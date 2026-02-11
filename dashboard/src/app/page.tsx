/**
 * Dashboard home page — platform-level overview.
 *
 * The main landing page for authenticated users. Displays aggregate
 * metrics across all stores, individual store cards with mini KPIs,
 * and quick action links.
 *
 * **For End Users:**
 *   This is your dashboard home. See an overview of all your stores'
 *   performance, then click into any store for details.
 *
 * **For QA Engineers:**
 *   - Protected page — unauthenticated users redirect to /login.
 *   - Store cards show name, status badge, and mini metrics.
 *   - Aggregate metrics sum across all stores.
 *   - "New Store" button navigates to /stores/new.
 *   - Renders inside the unified dashboard shell (sidebar + top bar).
 *
 * **For Developers:**
 *   - Fetches /api/v1/stores to list stores.
 *   - For each store, fetches analytics/summary for mini KPIs.
 *   - Uses StaggerChildren + staggerItem for card entrance animations.
 *   - Wrapped in AuthenticatedLayout for auth checks.
 *
 * @module app/page
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { FadeIn, StaggerChildren, staggerItem } from "@/components/motion-wrappers";
import { AuthenticatedLayout } from "@/components/authenticated-layout";
import { motion } from "motion/react";
import { api } from "@/lib/api";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Store,
  Plus,
  DollarSign,
  ShoppingCart,
  ArrowRight,
  BarChart3,
  Package,
  Globe,
} from "lucide-react";

/** Store record from the API. */
interface StoreItem {
  id: string;
  name: string;
  slug: string;
  niche: string;
  status: string;
  created_at: string;
}

/** Per-store analytics summary. */
interface StoreSummary {
  total_revenue: string | number;
  total_orders: number;
  total_products: number;
  average_order_value: string | number;
}

/** Combined store + analytics for display. */
interface StoreWithMetrics {
  store: StoreItem;
  metrics: StoreSummary | null;
}

/**
 * Dashboard home page component.
 *
 * Fetches all user stores, then fetches analytics for each to build
 * an aggregate overview and individual store cards.
 *
 * @returns The dashboard home page wrapped in AuthenticatedLayout.
 */
export default function Home() {
  const { user, loading: authLoading } = useAuth();
  const [storesWithMetrics, setStoresWithMetrics] = useState<StoreWithMetrics[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading || !user) return;

    async function fetchData() {
      const storesRes = await api.get<{ items: StoreItem[] } | StoreItem[]>("/api/v1/stores");
      if (!storesRes.data) {
        setLoading(false);
        return;
      }

      const stores: StoreItem[] = Array.isArray(storesRes.data)
        ? storesRes.data
        : storesRes.data.items ?? [];

      // Fetch analytics for each store in parallel.
      const results = await Promise.all(
        stores.map(async (store) => {
          const analyticsRes = await api.get<StoreSummary>(
            `/api/v1/stores/${store.id}/analytics/summary`
          );
          return { store, metrics: analyticsRes.data ?? null };
        })
      );

      setStoresWithMetrics(results);
      setLoading(false);
    }

    fetchData();
  }, [user, authLoading]);

  // Aggregate metrics across all stores.
  const totalRevenue = storesWithMetrics.reduce(
    (sum, s) => sum + (s.metrics ? Number(s.metrics.total_revenue) : 0),
    0
  );
  const totalOrders = storesWithMetrics.reduce(
    (sum, s) => sum + (s.metrics?.total_orders ?? 0),
    0
  );
  const totalProducts = storesWithMetrics.reduce(
    (sum, s) => sum + (s.metrics?.total_products ?? 0),
    0
  );
  const activeStores = storesWithMetrics.filter(
    (s) => s.store.status === "active"
  ).length;

  return (
    <AuthenticatedLayout>
      <div className="mx-auto max-w-4xl px-6 py-8 space-y-8">
        {/* Header */}
        <FadeIn>
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <h2 className="font-heading text-2xl font-bold tracking-tight">
                Welcome back
                {user?.email ? `, ${user.email.split("@")[0]}` : ""}
              </h2>
              <p className="text-muted-foreground">
                Here&apos;s an overview of your stores.
              </p>
            </div>
            <Link href="/stores/new">
              <Button size="sm" className="gap-1.5">
                <Plus className="h-3.5 w-3.5" />
                New Store
              </Button>
            </Link>
          </div>
        </FadeIn>

        {loading ? (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i}>
                <CardContent className="pt-5 pb-4">
                  <div className="animate-pulse space-y-2">
                    <div className="h-3 w-16 rounded bg-muted" />
                    <div className="h-7 w-24 rounded bg-muted" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <>
            {/* Aggregate KPIs */}
            <StaggerChildren className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                {
                  label: "Total Revenue",
                  value: `$${totalRevenue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
                  icon: DollarSign,
                  color: "text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30",
                },
                {
                  label: "Total Orders",
                  value: totalOrders.toLocaleString(),
                  icon: ShoppingCart,
                  color: "text-blue-600 bg-blue-100 dark:bg-blue-900/30",
                },
                {
                  label: "Products",
                  value: totalProducts.toLocaleString(),
                  icon: Package,
                  color: "text-purple-600 bg-purple-100 dark:bg-purple-900/30",
                },
                {
                  label: "Active Stores",
                  value: String(activeStores),
                  icon: Globe,
                  color: "text-amber-600 bg-amber-100 dark:bg-amber-900/30",
                },
              ].map((kpi) => (
                <motion.div key={kpi.label} variants={staggerItem}>
                  <Card>
                    <CardContent className="pt-5 pb-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
                            {kpi.label}
                          </p>
                          <p className="text-2xl font-bold mt-1 tabular-nums">
                            {kpi.value}
                          </p>
                        </div>
                        <div className={`p-2 rounded-lg ${kpi.color}`}>
                          <kpi.icon className="h-4 w-4" />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </StaggerChildren>

            {/* Store Cards */}
            {storesWithMetrics.length > 0 ? (
              <div className="space-y-3">
                <FadeIn delay={0.2}>
                  <h3 className="font-heading text-lg font-semibold">Your Stores</h3>
                </FadeIn>
                <StaggerChildren className="grid gap-3">
                  {storesWithMetrics.map(({ store: s, metrics }) => (
                    <motion.div key={s.id} variants={staggerItem}>
                      <Link href={`/stores/${s.id}`} className="group block">
                        <Card className="transition-all hover:shadow-md hover:-translate-y-0.5">
                          <CardContent className="py-4 px-5">
                            <div className="flex items-center gap-4">
                              {/* Store icon */}
                              <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
                                <Store className="size-5" />
                              </div>

                              {/* Name + niche */}
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <h4 className="font-heading font-semibold truncate">
                                    {s.name}
                                  </h4>
                                  <Badge
                                    variant={s.status === "active" ? "default" : "secondary"}
                                    className="shrink-0 text-[10px]"
                                  >
                                    {s.status}
                                  </Badge>
                                </div>
                                <p className="text-xs text-muted-foreground capitalize">
                                  {s.niche}
                                </p>
                              </div>

                              {/* Mini metrics */}
                              {metrics && (
                                <div className="hidden sm:flex items-center gap-6 text-right">
                                  <div>
                                    <p className="text-xs text-muted-foreground">Revenue</p>
                                    <p className="text-sm font-semibold tabular-nums">
                                      ${Number(metrics.total_revenue).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                                    </p>
                                  </div>
                                  <div>
                                    <p className="text-xs text-muted-foreground">Orders</p>
                                    <p className="text-sm font-semibold tabular-nums">
                                      {metrics.total_orders}
                                    </p>
                                  </div>
                                  <div>
                                    <p className="text-xs text-muted-foreground">Products</p>
                                    <p className="text-sm font-semibold tabular-nums">
                                      {metrics.total_products}
                                    </p>
                                  </div>
                                </div>
                              )}

                              {/* Arrow */}
                              <ArrowRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-1 shrink-0" />
                            </div>
                          </CardContent>
                        </Card>
                      </Link>
                    </motion.div>
                  ))}
                </StaggerChildren>
              </div>
            ) : (
              <FadeIn delay={0.2}>
                <Card>
                  <CardContent className="py-12 text-center">
                    <Store className="mx-auto h-10 w-10 text-muted-foreground mb-3" />
                    <h3 className="font-heading font-semibold mb-1">No stores yet</h3>
                    <p className="text-sm text-muted-foreground mb-4">
                      Create your first store to get started.
                    </p>
                    <Link href="/stores/new">
                      <Button size="sm" className="gap-1.5">
                        <Plus className="h-3.5 w-3.5" />
                        Create Store
                      </Button>
                    </Link>
                  </CardContent>
                </Card>
              </FadeIn>
            )}

            {/* Quick Links */}
            <FadeIn delay={0.3}>
              <div className="grid gap-3 sm:grid-cols-2">
                <Link href="/billing" className="group">
                  <div className="flex items-center gap-3 rounded-lg border bg-card/80 p-4 transition-all hover:shadow-sm hover:-translate-y-0.5">
                    <BarChart3 className="size-4 text-muted-foreground" />
                    <span className="text-sm font-medium">Billing & Subscription</span>
                    <ArrowRight className="ml-auto size-3.5 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
                  </div>
                </Link>
                <Link href="/stores" className="group">
                  <div className="flex items-center gap-3 rounded-lg border bg-card/80 p-4 transition-all hover:shadow-sm hover:-translate-y-0.5">
                    <Store className="size-4 text-muted-foreground" />
                    <span className="text-sm font-medium">All Stores</span>
                    <ArrowRight className="ml-auto size-3.5 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
                  </div>
                </Link>
              </div>
            </FadeIn>
          </>
        )}
      </div>
    </AuthenticatedLayout>
  );
}
