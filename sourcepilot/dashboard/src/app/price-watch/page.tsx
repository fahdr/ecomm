/**
 * Price Monitoring page — track supplier price changes for imported products.
 *
 * Users add products to their watch list and SourcePilot periodically checks
 * for price changes. Price alerts help merchants maintain healthy margins
 * by detecting cost increases or competitor price drops.
 *
 * **For Developers:**
 *   - `GET /api/v1/price-watches` — list all active watches.
 *   - `POST /api/v1/price-watches` — add a new watch (product URL + source).
 *   - `DELETE /api/v1/price-watches/{id}` — remove a watch.
 *   - `POST /api/v1/price-watches/sync` — trigger immediate price check for all watches.
 *   - Each watch includes current_price, last_price, and price_change fields.
 *   - Positive change = price went up (bad), negative = price went down (good).
 *
 * **For Project Managers:**
 *   - Price monitoring is a retention feature — keeps users engaged.
 *   - "Sync Now" provides on-demand checking for pro/enterprise users.
 *   - Price change indicators use color coding for quick visual scanning.
 *
 * **For QA Engineers:**
 *   - Test adding a watch with valid and invalid URLs.
 *   - Verify price change arrows point correct direction (up = red, down = green).
 *   - Test "Sync Now" button shows loading state.
 *   - Test deleting a watch removes it from the list.
 *   - Verify empty state when no watches exist.
 *   - Test with products that have no price change (should show neutral state).
 *
 * **For End Users:**
 *   - Add products to your watch list to track price changes over time.
 *   - Green arrows mean the price dropped (good for your margins).
 *   - Red arrows mean the price increased (review your markup).
 *   - Click "Sync Now" to check prices immediately.
 */

"use client";

import * as React from "react";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Plus,
  Trash2,
  Loader2,
  RefreshCw,
  Eye,
} from "lucide-react";
import { Shell } from "@/components/shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  FadeIn,
  StaggerChildren,
  AnimatedCounter,
  PageTransition,
} from "@/components/motion";
import { api } from "@/lib/api";

/** Shape of a price watch from the API. */
interface PriceWatch {
  id: string;
  product_title: string;
  product_url: string;
  source: string;
  current_price: number;
  last_price: number;
  currency: string;
  price_change: number;
  price_change_percent: number;
  last_checked?: string;
  created_at: string;
}

/** Form data for adding a new price watch. */
interface WatchForm {
  product_url: string;
  source: string;
}

/** Available supplier sources. */
const SOURCES = [
  { value: "aliexpress", label: "AliExpress" },
  { value: "cj", label: "CJ Dropshipping" },
  { value: "spocket", label: "Spocket" },
];

/**
 * Get the price change indicator direction and color.
 *
 * @param change - The price change amount (positive = increase, negative = decrease).
 * @returns An object with the icon component and CSS color class.
 */
function getPriceIndicator(change: number): {
  icon: React.ReactNode;
  colorClass: string;
  label: string;
} {
  if (change > 0) {
    return {
      icon: <TrendingUp className="size-4" />,
      colorClass: "text-red-500",
      label: "Price increased",
    };
  } else if (change < 0) {
    return {
      icon: <TrendingDown className="size-4" />,
      colorClass: "text-emerald-500",
      label: "Price decreased",
    };
  }
  return {
    icon: <Minus className="size-4" />,
    colorClass: "text-muted-foreground",
    label: "No change",
  };
}

/**
 * Price Monitoring page component.
 *
 * @returns The price watch page wrapped in the Shell layout.
 */
export default function PriceWatchPage() {
  const [watches, setWatches] = React.useState<PriceWatch[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [syncing, setSyncing] = React.useState(false);

  /** Dialog state for adding a new watch. */
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);
  const [deletingId, setDeletingId] = React.useState<string | null>(null);

  /** Form state for the "Add Watch" dialog. */
  const [form, setForm] = React.useState<WatchForm>({
    product_url: "",
    source: "aliexpress",
  });

  /**
   * Fetch all price watches from the API.
   */
  const fetchWatches = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    const { data, error: apiError } = await api.get<PriceWatch[]>(
      "/api/v1/price-watches"
    );
    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setWatches(data);
    }
    setLoading(false);
  }, []);

  React.useEffect(() => {
    fetchWatches();
  }, [fetchWatches]);

  /** Compute summary stats from the watches list. */
  const stats = React.useMemo(() => {
    const total = watches.length;
    const priceUp = watches.filter((w) => w.price_change > 0).length;
    const priceDown = watches.filter((w) => w.price_change < 0).length;
    const stable = watches.filter((w) => w.price_change === 0).length;
    return { total, priceUp, priceDown, stable };
  }, [watches]);

  /**
   * Submit the add watch form to the API.
   */
  async function handleAddWatch() {
    if (!form.product_url.trim()) return;

    setSubmitting(true);
    const { error: apiError } = await api.post("/api/v1/price-watches", {
      product_url: form.product_url.trim(),
      source: form.source,
    });

    setSubmitting(false);
    if (!apiError) {
      setDialogOpen(false);
      setForm({ product_url: "", source: "aliexpress" });
      fetchWatches();
    }
  }

  /**
   * Delete a price watch.
   *
   * @param id - The watch ID to remove.
   */
  async function handleDelete(id: string) {
    setDeletingId(id);
    await api.del(`/api/v1/price-watches/${id}`);
    setDeletingId(null);
    fetchWatches();
  }

  /**
   * Trigger an immediate price sync for all watches.
   */
  async function handleSync() {
    setSyncing(true);
    await api.post("/api/v1/price-watches/sync");
    setSyncing(false);
    fetchWatches();
  }

  /**
   * Format a relative time string from an ISO timestamp.
   *
   * @param dateStr - ISO date string.
   * @returns A human-readable relative time.
   */
  function formatRelativeTime(dateStr: string): string {
    const now = Date.now();
    const then = new Date(dateStr).getTime();
    const diffMs = now - then;
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  }

  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* ── Header ── */}
        <FadeIn direction="down">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight">
                Price Watch
              </h2>
              <p className="text-muted-foreground mt-1">
                Monitor supplier price changes for your tracked products
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                onClick={handleSync}
                disabled={syncing || watches.length === 0}
              >
                {syncing ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <RefreshCw className="size-4" />
                )}
                {syncing ? "Syncing..." : "Sync Now"}
              </Button>
              <Button onClick={() => setDialogOpen(true)}>
                <Plus className="size-4" />
                Add Watch
              </Button>
            </div>
          </div>
        </FadeIn>

        {/* ── Summary Cards ── */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-4 w-20" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-8 w-16" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <StaggerChildren
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
            staggerDelay={0.08}
          >
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Total Watches
                </CardTitle>
                <Eye className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <AnimatedCounter
                  value={stats.total}
                  className="text-3xl font-bold font-heading"
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Price Increased
                </CardTitle>
                <TrendingUp className="size-4 text-red-500" />
              </CardHeader>
              <CardContent>
                <AnimatedCounter
                  value={stats.priceUp}
                  className="text-3xl font-bold font-heading text-red-500"
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Price Decreased
                </CardTitle>
                <TrendingDown className="size-4 text-emerald-500" />
              </CardHeader>
              <CardContent>
                <AnimatedCounter
                  value={stats.priceDown}
                  className="text-3xl font-bold font-heading text-emerald-500"
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Stable
                </CardTitle>
                <Minus className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <AnimatedCounter
                  value={stats.stable}
                  className="text-3xl font-bold font-heading"
                />
              </CardContent>
            </Card>
          </StaggerChildren>
        )}

        {/* ── Error State ── */}
        {error && (
          <FadeIn>
            <Card className="border-destructive/50">
              <CardContent className="pt-6">
                <p className="text-destructive text-sm">
                  Failed to load price watches: {error}
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={fetchWatches}
                >
                  Retry
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        )}

        {/* ── Watch List ── */}
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Card key={i}>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-4">
                    <Skeleton className="size-10 rounded" />
                    <div className="flex-1 space-y-2">
                      <Skeleton className="h-4 w-48" />
                      <Skeleton className="h-3 w-32" />
                    </div>
                    <Skeleton className="h-6 w-24" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : watches.length === 0 && !error ? (
          /* ── Empty State ── */
          <FadeIn>
            <Card>
              <CardContent className="pt-6 text-center py-12">
                <TrendingUp className="size-12 text-muted-foreground/40 mx-auto mb-4" />
                <h3 className="font-heading text-lg font-semibold mb-2">
                  No price watches yet
                </h3>
                <p className="text-muted-foreground text-sm mb-4">
                  Add products to your watch list to track supplier price changes
                  and protect your margins.
                </p>
                <Button onClick={() => setDialogOpen(true)}>
                  <Plus className="size-4" />
                  Add Your First Watch
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        ) : (
          <FadeIn delay={0.2}>
            <div className="space-y-3">
              {watches.map((watch) => {
                const indicator = getPriceIndicator(watch.price_change);
                const isDeleting = deletingId === watch.id;

                return (
                  <Card
                    key={watch.id}
                    className="hover:border-primary/30 transition-colors"
                  >
                    <CardContent className="pt-6">
                      <div className="flex items-center gap-4">
                        {/* Price change indicator */}
                        <div
                          className={`size-10 rounded-lg flex items-center justify-center shrink-0 ${
                            watch.price_change > 0
                              ? "bg-red-500/10"
                              : watch.price_change < 0
                                ? "bg-emerald-500/10"
                                : "bg-secondary"
                          }`}
                        >
                          <span className={indicator.colorClass}>
                            {indicator.icon}
                          </span>
                        </div>

                        {/* Product Details */}
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm truncate">
                            {watch.product_title}
                          </p>
                          <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                            <span className="capitalize">{watch.source}</span>
                            {watch.last_checked && (
                              <>
                                <span>&middot;</span>
                                <span>
                                  Checked {formatRelativeTime(watch.last_checked)}
                                </span>
                              </>
                            )}
                          </div>
                        </div>

                        {/* Price Info */}
                        <div className="text-right shrink-0">
                          <div className="flex items-center gap-2 justify-end">
                            <span className="font-heading font-bold text-lg">
                              ${watch.current_price.toFixed(2)}
                            </span>
                            {watch.price_change !== 0 && (
                              <Badge
                                variant={
                                  watch.price_change > 0
                                    ? "destructive"
                                    : "success"
                                }
                                className="text-xs"
                              >
                                {watch.price_change > 0 ? "+" : ""}
                                {watch.price_change_percent.toFixed(1)}%
                              </Badge>
                            )}
                          </div>
                          {watch.last_price !== watch.current_price && (
                            <p className="text-xs text-muted-foreground line-through mt-0.5">
                              ${watch.last_price.toFixed(2)}
                            </p>
                          )}
                        </div>

                        {/* Delete Action */}
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Remove watch"
                          onClick={() => handleDelete(watch.id)}
                          disabled={isDeleting}
                          className="shrink-0"
                        >
                          {isDeleting ? (
                            <Loader2 className="size-4 animate-spin" />
                          ) : (
                            <Trash2 className="size-4 text-muted-foreground hover:text-destructive" />
                          )}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </FadeIn>
        )}

        {/* ── Add Watch Dialog ── */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="font-heading">Add Price Watch</DialogTitle>
              <DialogDescription>
                Enter a product URL to start monitoring its price. SourcePilot
                will check for changes periodically.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2">
              {/* Source */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Source</label>
                <select
                  value={form.source}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, source: e.target.value }))
                  }
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {SOURCES.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Product URL */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Product URL</label>
                <Input
                  type="url"
                  placeholder="https://www.aliexpress.com/item/..."
                  value={form.product_url}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      product_url: e.target.value,
                    }))
                  }
                />
              </div>
            </div>

            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setDialogOpen(false)}
                disabled={submitting}
              >
                Cancel
              </Button>
              <Button
                onClick={handleAddWatch}
                disabled={submitting || !form.product_url.trim()}
              >
                {submitting ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Eye className="size-4" />
                )}
                {submitting ? "Adding..." : "Add Watch"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageTransition>
    </Shell>
  );
}
