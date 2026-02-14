/**
 * Competitors page — manage and monitor competitor stores.
 *
 * Displays a table of all tracked competitor stores with status badges,
 * product counts, and last scan timestamps. Users can add new competitors,
 * edit existing ones, pause monitoring, and delete competitors through
 * an inline dialog form.
 *
 * **For Developers:**
 *   - Fetches from `GET /api/v1/competitors/` with pagination.
 *   - Create via `POST /api/v1/competitors/` with name, URL, and platform.
 *   - Delete via `DELETE /api/v1/competitors/{id}` with confirmation.
 *   - Uses Shell wrapper for authenticated layout with sidebar.
 *   - Motion animations: PageTransition wraps the page, StaggerChildren
 *     provides cascading table row reveals, FadeIn for the header area.
 *   - Loading state shows animated skeleton rows.
 *
 * **For Project Managers:**
 *   - Competitors are the core resource — this page is where users
 *     start their monitoring workflow.
 *   - Plan limits are enforced server-side; the UI shows an error
 *     toast if the limit is hit.
 *
 * **For QA Engineers:**
 *   - Verify the add competitor form validates required fields.
 *   - Test pagination by creating many competitors.
 *   - Verify delete confirmation dialog prevents accidental deletion.
 *   - Check that the page handles API errors gracefully (error card).
 *   - Verify that new competitors appear immediately after creation.
 *   - Test platform selector values (shopify, woocommerce, custom).
 *
 * **For End Users:**
 *   - Add competitor stores to start monitoring their products and prices.
 *   - Click a competitor to view its tracked products.
 *   - Use the pause/resume toggle to temporarily stop scanning.
 *   - Delete competitors you no longer want to track.
 */

"use client";

import * as React from "react";
import Link from "next/link";
import {
  Plus,
  Users,
  ExternalLink,
  Trash2,
  Pause,
  Play,
  Radar,
  RefreshCw,
  Store,
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
  DialogClose,
} from "@/components/ui/dialog";
import {
  FadeIn,
  StaggerChildren,
  PageTransition,
  AnimatedCounter,
} from "@/components/motion";
import { api } from "@/lib/api";
import { serviceConfig } from "@/service.config";

// ── Types ────────────────────────────────────────────────────────────

/** Shape of a single competitor from the API. */
interface Competitor {
  /** Unique identifier (UUID). */
  id: string;
  /** Competitor store name. */
  name: string;
  /** Store URL. */
  url: string;
  /** E-commerce platform (shopify, woocommerce, custom). */
  platform: string;
  /** Timestamp of the most recent scan, or null. */
  last_scanned: string | null;
  /** Monitoring status: active, paused, or error. */
  status: string;
  /** Number of tracked products. */
  product_count: number;
  /** When the competitor record was created. */
  created_at: string;
  /** Last update timestamp. */
  updated_at: string;
}

/** Paginated competitor list response from the API. */
interface CompetitorListResponse {
  items: Competitor[];
  total: number;
  page: number;
  per_page: number;
}

// ── Constants ────────────────────────────────────────────────────────

/** Available e-commerce platform options for the competitor form. */
const PLATFORM_OPTIONS = [
  { value: "shopify", label: "Shopify" },
  { value: "woocommerce", label: "WooCommerce" },
  { value: "custom", label: "Custom / Other" },
];

// ── Component ────────────────────────────────────────────────────────

/**
 * Competitors page component.
 *
 * Displays the competitor table, add competitor dialog, and inline
 * action buttons for each competitor row.
 *
 * @returns The competitors page wrapped in the Shell layout.
 */
export default function CompetitorsPage() {
  const [competitors, setCompetitors] = React.useState<Competitor[]>([]);
  const [total, setTotal] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  // Add competitor dialog state
  const [addOpen, setAddOpen] = React.useState(false);
  const [addName, setAddName] = React.useState("");
  const [addUrl, setAddUrl] = React.useState("");
  const [addPlatform, setAddPlatform] = React.useState("shopify");
  const [addLoading, setAddLoading] = React.useState(false);
  const [addError, setAddError] = React.useState<string | null>(null);

  // Delete confirmation state
  const [deleteTarget, setDeleteTarget] = React.useState<Competitor | null>(null);
  const [deleteLoading, setDeleteLoading] = React.useState(false);

  const perPage = 20;

  /**
   * Fetch the paginated competitor list from the API.
   * Updates competitors, total, loading, and error state.
   */
  const fetchCompetitors = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    const { data, error: apiError } = await api.get<CompetitorListResponse>(
      `/api/v1/competitors/?page=${page}&per_page=${perPage}`
    );
    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setCompetitors(data.items);
      setTotal(data.total);
    }
    setLoading(false);
  }, [page]);

  React.useEffect(() => {
    fetchCompetitors();
  }, [fetchCompetitors]);

  /**
   * Handle the add competitor form submission.
   * Validates inputs, calls the API, refreshes the list on success.
   */
  async function handleAddCompetitor() {
    if (!addName.trim() || !addUrl.trim()) {
      setAddError("Name and URL are required.");
      return;
    }

    setAddLoading(true);
    setAddError(null);

    const { data, error: apiError } = await api.post<Competitor>(
      "/api/v1/competitors/",
      { name: addName.trim(), url: addUrl.trim(), platform: addPlatform }
    );

    if (apiError) {
      setAddError(apiError.message);
      setAddLoading(false);
      return;
    }

    // Reset form and close dialog
    setAddName("");
    setAddUrl("");
    setAddPlatform("shopify");
    setAddOpen(false);
    setAddLoading(false);

    // Refresh the list
    fetchCompetitors();
  }

  /**
   * Toggle a competitor's monitoring status between 'active' and 'paused'.
   *
   * @param competitor - The competitor to toggle.
   */
  async function handleToggleStatus(competitor: Competitor) {
    const newStatus = competitor.status === "active" ? "paused" : "active";
    const { error: apiError } = await api.patch<Competitor>(
      `/api/v1/competitors/${competitor.id}`,
      { status: newStatus }
    );
    if (!apiError) {
      fetchCompetitors();
    }
  }

  /**
   * Delete a competitor after confirmation.
   * Closes the confirmation dialog and refreshes the list.
   */
  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleteLoading(true);
    await api.del(`/api/v1/competitors/${deleteTarget.id}`);
    setDeleteTarget(null);
    setDeleteLoading(false);
    fetchCompetitors();
  }

  /**
   * Get the visual badge variant for a competitor status.
   *
   * @param status - The competitor's monitoring status.
   * @returns The Badge variant name.
   */
  function getStatusVariant(status: string) {
    switch (status) {
      case "active":
        return "success" as const;
      case "paused":
        return "secondary" as const;
      case "error":
        return "destructive" as const;
      default:
        return "outline" as const;
    }
  }

  /**
   * Format a platform identifier into a display-friendly label.
   *
   * @param platform - The platform identifier (shopify, woocommerce, custom).
   * @returns Capitalized platform label.
   */
  function formatPlatform(platform: string): string {
    return PLATFORM_OPTIONS.find((p) => p.value === platform)?.label || platform;
  }

  /**
   * Format a timestamp into a human-readable relative or absolute string.
   *
   * @param dateStr - ISO date string or null.
   * @returns Formatted date string or "Never" if null.
   */
  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "Never";
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    if (diffHours < 1) return "Just now";
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  }

  const totalPages = Math.ceil(total / perPage);

  return (
    <Shell>
      <PageTransition className="p-6 space-y-6">
        {/* ── Header ── */}
        <FadeIn direction="down">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight flex items-center gap-2">
                <Users className="size-6 text-primary" />
                Competitors
              </h2>
              <p className="text-muted-foreground mt-1">
                Monitor competitor stores, track products, and detect price changes.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={fetchCompetitors}
                disabled={loading}
              >
                <RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} />
                Refresh
              </Button>
              <Button onClick={() => setAddOpen(true)}>
                <Plus className="size-4" />
                Add Competitor
              </Button>
            </div>
          </div>
        </FadeIn>

        {/* ── Summary Cards ── */}
        <FadeIn delay={0.1}>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Total Competitors
                </CardTitle>
                <Store className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <AnimatedCounter
                  value={total}
                  className="text-3xl font-bold font-heading"
                />
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Active Monitoring
                </CardTitle>
                <Radar className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <AnimatedCounter
                  value={competitors.filter((c) => c.status === "active").length}
                  className="text-3xl font-bold font-heading text-emerald-600"
                />
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Total Products Tracked
                </CardTitle>
                <Users className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <AnimatedCounter
                  value={competitors.reduce((sum, c) => sum + c.product_count, 0)}
                  className="text-3xl font-bold font-heading"
                />
              </CardContent>
            </Card>
          </div>
        </FadeIn>

        {/* ── Competitor Table ── */}
        {loading ? (
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-4">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-4">
                    <Skeleton className="h-10 w-10 rounded-lg" />
                    <div className="flex-1 space-y-2">
                      <Skeleton className="h-4 w-48" />
                      <Skeleton className="h-3 w-72" />
                    </div>
                    <Skeleton className="h-6 w-16 rounded-full" />
                    <Skeleton className="h-8 w-20" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ) : error ? (
          <FadeIn>
            <Card className="border-destructive/50">
              <CardContent className="pt-6">
                <p className="text-destructive text-sm">
                  Failed to load competitors: {error}
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={fetchCompetitors}
                >
                  Retry
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        ) : competitors.length === 0 ? (
          <FadeIn>
            <Card className="border-dashed">
              <CardContent className="pt-6 pb-6 text-center">
                <Store className="size-12 text-muted-foreground mx-auto mb-4 opacity-40" />
                <h3 className="font-heading text-lg font-semibold">
                  No competitors yet
                </h3>
                <p className="text-muted-foreground text-sm mt-1 max-w-md mx-auto">
                  Add your first competitor store to start monitoring their products,
                  prices, and inventory changes.
                </p>
                <Button className="mt-4" onClick={() => setAddOpen(true)}>
                  <Plus className="size-4" />
                  Add Your First Competitor
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        ) : (
          <Card>
            <CardContent className="pt-6">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-muted-foreground">
                      <th className="text-left py-3 px-4 font-medium">Store</th>
                      <th className="text-left py-3 px-4 font-medium">Platform</th>
                      <th className="text-left py-3 px-4 font-medium">Status</th>
                      <th className="text-right py-3 px-4 font-medium">Products</th>
                      <th className="text-left py-3 px-4 font-medium">Last Scanned</th>
                      <th className="text-right py-3 px-4 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    <StaggerChildren staggerDelay={0.04}>
                      {competitors.map((competitor) => (
                        <tr
                          key={competitor.id}
                          className="border-b last:border-0 hover:bg-secondary/30 transition-colors"
                        >
                          <td className="py-3 px-4">
                            <div>
                              <Link
                                href={`/competitors/${competitor.id}/products`}
                                className="font-medium hover:text-primary transition-colors"
                              >
                                {competitor.name}
                              </Link>
                              <div className="flex items-center gap-1 mt-0.5">
                                <span className="text-xs text-muted-foreground truncate max-w-[260px]">
                                  {competitor.url}
                                </span>
                                <a
                                  href={competitor.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-muted-foreground hover:text-primary"
                                >
                                  <ExternalLink className="size-3" />
                                </a>
                              </div>
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            <Badge variant="outline" className="text-xs">
                              {formatPlatform(competitor.platform)}
                            </Badge>
                          </td>
                          <td className="py-3 px-4">
                            <Badge variant={getStatusVariant(competitor.status)}>
                              {competitor.status}
                            </Badge>
                          </td>
                          <td className="py-3 px-4 text-right font-mono">
                            {competitor.product_count}
                          </td>
                          <td className="py-3 px-4 text-muted-foreground text-xs">
                            {formatDate(competitor.last_scanned)}
                          </td>
                          <td className="py-3 px-4">
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="icon"
                                className="size-8"
                                onClick={() => handleToggleStatus(competitor)}
                                title={
                                  competitor.status === "active"
                                    ? "Pause monitoring"
                                    : "Resume monitoring"
                                }
                              >
                                {competitor.status === "active" ? (
                                  <Pause className="size-3.5" />
                                ) : (
                                  <Play className="size-3.5" />
                                )}
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="size-8 text-destructive hover:text-destructive"
                                onClick={() => setDeleteTarget(competitor)}
                                title="Delete competitor"
                              >
                                <Trash2 className="size-3.5" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </StaggerChildren>
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t">
                  <p className="text-sm text-muted-foreground">
                    Showing {(page - 1) * perPage + 1}–
                    {Math.min(page * perPage, total)} of {total}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page <= 1}
                      onClick={() => setPage((p) => p - 1)}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page >= totalPages}
                      onClick={() => setPage((p) => p + 1)}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* ── Add Competitor Dialog ── */}
        <Dialog open={addOpen} onOpenChange={setAddOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Competitor Store</DialogTitle>
              <DialogDescription>
                Enter the details of the competitor store you want to monitor.
                SpyDrop will scan it regularly for products and price changes.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="comp-name">
                  Store Name
                </label>
                <Input
                  id="comp-name"
                  placeholder="e.g. Rival Gadgets"
                  value={addName}
                  onChange={(e) => setAddName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="comp-url">
                  Store URL
                </label>
                <Input
                  id="comp-url"
                  placeholder="https://rival-gadgets.com"
                  value={addUrl}
                  onChange={(e) => setAddUrl(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="comp-platform">
                  Platform
                </label>
                <select
                  id="comp-platform"
                  value={addPlatform}
                  onChange={(e) => setAddPlatform(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {PLATFORM_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
              {addError && (
                <p className="text-destructive text-sm">{addError}</p>
              )}
            </div>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline">Cancel</Button>
              </DialogClose>
              <Button onClick={handleAddCompetitor} disabled={addLoading}>
                {addLoading ? (
                  <RefreshCw className="size-4 animate-spin" />
                ) : (
                  <Plus className="size-4" />
                )}
                {addLoading ? "Adding..." : "Add Competitor"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* ── Delete Confirmation Dialog ── */}
        <Dialog
          open={!!deleteTarget}
          onOpenChange={(open) => !open && setDeleteTarget(null)}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Delete Competitor</DialogTitle>
              <DialogDescription>
                Are you sure you want to delete{" "}
                <strong>{deleteTarget?.name}</strong>? This will permanently
                remove all tracked products, scan history, and alerts for this
                competitor. This action cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteTarget(null)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleDelete}
                disabled={deleteLoading}
              >
                {deleteLoading ? (
                  <RefreshCw className="size-4 animate-spin" />
                ) : (
                  <Trash2 className="size-4" />
                )}
                {deleteLoading ? "Deleting..." : "Delete Permanently"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageTransition>
    </Shell>
  );
}
