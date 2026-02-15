/**
 * Watchlist page — manage tracked products from research results.
 *
 * Displays the user's saved products organized by status tabs (All, Watching,
 * Imported, Dismissed). Each item shows a product snapshot with score, price,
 * source, and user notes. Users can update status, edit notes, and remove items.
 *
 * **For Developers:**
 *   - Fetches from `GET /api/v1/watchlist` with optional `?status=` filter.
 *   - Updates items via `PATCH /api/v1/watchlist/{id}`.
 *   - Deletes items via `DELETE /api/v1/watchlist/{id}`.
 *   - Status tabs are implemented as simple state filters that re-fetch data.
 *   - Product score is displayed as a colored progress ring for quick scanning.
 *   - StaggerChildren provides cascading reveal for the product grid.
 *
 * **For Project Managers:**
 *   - The watchlist is how users save and organize promising products.
 *   - Watchlist capacity is limited by plan tier (free = 25, pro = 500).
 *   - Status workflow: watching -> imported (pushed to store) or dismissed.
 *
 * **For QA Engineers:**
 *   - Verify loading skeletons appear while data is being fetched.
 *   - Test tab switching: "Watching", "Imported", "Dismissed" filter correctly.
 *   - Test status update: clicking status buttons changes the item's status.
 *   - Test delete: item removed from list after confirmation.
 *   - Test with empty watchlist — shows helpful empty state.
 *   - Test pagination with many watchlist items.
 *   - Verify product cards display correct score, price, and source info.
 *
 * **For End Users:**
 *   - View all your saved products organized by status.
 *   - Click the status tabs to filter by Watching, Imported, or Dismissed.
 *   - Update a product's status as you evaluate and import products.
 *   - Add notes to remember why you saved a particular product.
 *   - Remove products you no longer want to track.
 */

"use client";

import * as React from "react";
import {
  Eye,
  PackageCheck,
  XCircle,
  Trash2,
  Loader2,
  ExternalLink,
  StickyNote,
  ChevronLeft,
  ChevronRight,
  Star,
  TrendingUp,
} from "lucide-react";
import { Shell } from "@/components/shell";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
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

/* ── Type Definitions ──────────────────────────────────────────────── */

/** Snapshot of the linked research result displayed on each watchlist card. */
interface ResultSnapshot {
  id: string;
  source: string;
  product_title: string;
  product_url: string;
  image_url: string | null;
  price: number | null;
  currency: string;
  score: number;
}

/** Shape of a watchlist item from the backend API. */
interface WatchlistItem {
  id: string;
  user_id: string;
  result_id: string;
  status: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
  result: ResultSnapshot | null;
}

/** Paginated list response from GET /api/v1/watchlist. */
interface WatchlistListResponse {
  items: WatchlistItem[];
  total: number;
  page: number;
  per_page: number;
}

/** Tab definitions for status filtering. */
const STATUS_TABS = [
  { key: null, label: "All", icon: Star },
  { key: "watching", label: "Watching", icon: Eye },
  { key: "imported", label: "Imported", icon: PackageCheck },
  { key: "dismissed", label: "Dismissed", icon: XCircle },
] as const;

/* ── Helper Functions ──────────────────────────────────────────────── */

/**
 * Get a color class for the product score value.
 *
 * @param score - Product composite score (0-100).
 * @returns Tailwind color class string.
 */
function getScoreColor(score: number): string {
  if (score >= 80) return "text-emerald-500";
  if (score >= 60) return "text-amber-500";
  if (score >= 40) return "text-orange-500";
  return "text-red-500";
}

/**
 * Get a background color class for the score ring.
 *
 * @param score - Product composite score (0-100).
 * @returns Tailwind background class string.
 */
function getScoreBgColor(score: number): string {
  if (score >= 80) return "bg-emerald-500";
  if (score >= 60) return "bg-amber-500";
  if (score >= 40) return "bg-orange-500";
  return "bg-red-500";
}

/**
 * Map a watchlist status to a Badge variant.
 *
 * @param status - The watchlist item status (watching, imported, dismissed).
 * @returns Badge variant and display label.
 */
function getStatusBadge(status: string): {
  variant: "secondary" | "success" | "destructive" | "outline";
  label: string;
} {
  switch (status) {
    case "imported":
      return { variant: "success", label: "Imported" };
    case "dismissed":
      return { variant: "destructive", label: "Dismissed" };
    case "watching":
    default:
      return { variant: "outline", label: "Watching" };
  }
}

/**
 * Format a price with its currency code.
 *
 * @param price - The product price (nullable).
 * @param currency - ISO 4217 currency code.
 * @returns Formatted price string or "N/A" if no price.
 */
function formatPrice(price: number | null, currency: string): string {
  if (price === null) return "N/A";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency || "USD",
    minimumFractionDigits: 2,
  }).format(price);
}

/**
 * Capitalize and clean a source identifier for display.
 *
 * @param source - Raw source identifier (e.g. "google_trends").
 * @returns Human-readable label (e.g. "Google Trends").
 */
function formatSource(source: string): string {
  return source
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/* ── Main Page Component ───────────────────────────────────────────── */

/**
 * Watchlist page component — manages tracked products with status filtering.
 *
 * @returns The watchlist page wrapped in the Shell layout.
 */
export default function WatchlistPage() {
  /* ── State ── */
  const [items, setItems] = React.useState<WatchlistItem[]>([]);
  const [total, setTotal] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [perPage] = React.useState(12);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [activeTab, setActiveTab] = React.useState<string | null>(null);

  /* Notes editing state */
  const [editingNotesId, setEditingNotesId] = React.useState<string | null>(null);
  const [notesInput, setNotesInput] = React.useState("");
  const [savingNotes, setSavingNotes] = React.useState(false);

  /* Status update and delete loading states */
  const [updatingId, setUpdatingId] = React.useState<string | null>(null);
  const [deletingId, setDeletingId] = React.useState<string | null>(null);

  /* ── Data Fetching ── */

  /**
   * Fetch watchlist items from the backend with current filters and pagination.
   */
  const fetchItems = React.useCallback(async () => {
    setLoading(true);
    setError(null);

    let path = `/api/v1/watchlist?page=${page}&per_page=${perPage}`;
    if (activeTab) {
      path += `&status=${activeTab}`;
    }

    const { data, error: apiError } =
      await api.get<WatchlistListResponse>(path);

    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setItems(data.items);
      setTotal(data.total);
    }
    setLoading(false);
  }, [page, perPage, activeTab]);

  React.useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  /* ── Handlers ── */

  /**
   * Switch the active status tab and reset to page 1.
   *
   * @param tabKey - The status filter key (null for "All").
   */
  function handleTabChange(tabKey: string | null) {
    setActiveTab(tabKey);
    setPage(1);
  }

  /**
   * Update a watchlist item's status via the API.
   *
   * @param itemId - The watchlist item UUID.
   * @param newStatus - The new status value.
   */
  async function handleStatusUpdate(itemId: string, newStatus: string) {
    setUpdatingId(itemId);

    const { error: apiError } = await api.patch<WatchlistItem>(
      `/api/v1/watchlist/${itemId}`,
      { status: newStatus }
    );

    if (!apiError) {
      fetchItems();
    }
    setUpdatingId(null);
  }

  /**
   * Open the notes editor for an item.
   *
   * @param item - The watchlist item to edit notes for.
   */
  function openNotesEditor(item: WatchlistItem) {
    setEditingNotesId(item.id);
    setNotesInput(item.notes || "");
  }

  /**
   * Save updated notes for the currently editing item.
   */
  async function handleSaveNotes() {
    if (!editingNotesId) return;
    setSavingNotes(true);

    const { error: apiError } = await api.patch<WatchlistItem>(
      `/api/v1/watchlist/${editingNotesId}`,
      { notes: notesInput || null }
    );

    if (!apiError) {
      fetchItems();
    }
    setSavingNotes(false);
    setEditingNotesId(null);
  }

  /**
   * Delete a watchlist item by ID and refresh the list.
   *
   * @param itemId - The watchlist item UUID to remove.
   */
  async function handleDelete(itemId: string) {
    setDeletingId(itemId);

    const { error: apiError } = await api.del(`/api/v1/watchlist/${itemId}`);

    if (!apiError) {
      fetchItems();
    }
    setDeletingId(null);
  }

  /* ── Derived Values ── */
  const totalPages = Math.ceil(total / perPage);

  /* ── Render ── */
  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* ── Page Header ── */}
        <FadeIn direction="down">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight flex items-center gap-2">
                <Eye className="size-6" />
                Watchlist
              </h2>
              <p className="text-muted-foreground mt-1">
                Track and organize your most promising product discoveries.
              </p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold font-heading">
                {loading ? (
                  <Skeleton className="h-8 w-12 inline-block" />
                ) : (
                  <AnimatedCounter value={total} />
                )}
              </p>
              <p className="text-xs text-muted-foreground">items tracked</p>
            </div>
          </div>
        </FadeIn>

        {/* ── Status Tabs ── */}
        <FadeIn delay={0.1}>
          <div className="flex items-center gap-2 border-b pb-1">
            {STATUS_TABS.map((tab) => {
              const isActive = activeTab === tab.key;
              const TabIcon = tab.icon;
              return (
                <button
                  key={tab.label}
                  onClick={() => handleTabChange(tab.key)}
                  className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-t-lg transition-colors border-b-2 -mb-[3px] ${
                    isActive
                      ? "border-primary text-primary bg-primary/5"
                      : "border-transparent text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                  }`}
                >
                  <TabIcon className="size-3.5" />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </FadeIn>

        {/* ── Content Area ── */}
        {loading ? (
          /* Loading skeleton grid */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Card key={i}>
                <CardContent className="pt-6 space-y-3">
                  <div className="flex items-start justify-between">
                    <Skeleton className="h-5 w-3/4" />
                    <Skeleton className="size-10 rounded-full" />
                  </div>
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-4 w-32" />
                  <div className="flex gap-2 pt-2">
                    <Skeleton className="h-8 w-20" />
                    <Skeleton className="h-8 w-20" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : error ? (
          /* Error state */
          <FadeIn>
            <Card className="border-destructive/50">
              <CardContent className="pt-6 text-center py-12">
                <XCircle className="size-10 text-destructive mx-auto mb-3" />
                <p className="text-destructive text-sm">{error}</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-4"
                  onClick={() => fetchItems()}
                >
                  Retry
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        ) : items.length === 0 ? (
          /* Empty state */
          <FadeIn>
            <div className="text-center py-20">
              <div className="size-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
                <TrendingUp className="size-7 text-primary" />
              </div>
              <h3 className="font-heading font-semibold text-lg">
                {activeTab
                  ? `No ${activeTab} items`
                  : "Your watchlist is empty"}
              </h3>
              <p className="text-muted-foreground text-sm mt-1 max-w-sm mx-auto">
                {activeTab
                  ? `You don't have any products with "${activeTab}" status. Switch tabs or run a research to find products.`
                  : "Save promising products from your research results to start building your watchlist."}
              </p>
              {!activeTab && (
                <Button className="mt-5" asChild>
                  <a href="/research">
                    <TrendingUp className="size-4" />
                    Start Research
                  </a>
                </Button>
              )}
            </div>
          </FadeIn>
        ) : (
          /* Watchlist product cards grid */
          <>
            <StaggerChildren
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
              staggerDelay={0.06}
            >
              {items.map((item) => {
                const result = item.result;
                const { variant, label } = getStatusBadge(item.status);
                const score = result?.score ?? 0;

                return (
                  <Card
                    key={item.id}
                    className="group hover:shadow-md transition-shadow duration-200"
                  >
                    <CardContent className="pt-6 space-y-3">
                      {/* Top row: title + score */}
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <p className="font-medium text-sm leading-snug line-clamp-2">
                            {result?.product_title || "Unknown Product"}
                          </p>
                          <div className="flex items-center gap-2 mt-1.5">
                            <Badge variant={variant} className="text-xs">
                              {label}
                            </Badge>
                            {result && (
                              <span className="text-xs text-muted-foreground">
                                {formatSource(result.source)}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Score circle */}
                        <div className="relative shrink-0">
                          <div className="size-12 rounded-full border-[3px] border-secondary flex items-center justify-center relative overflow-hidden">
                            {/* Filled arc using conic-gradient */}
                            <div
                              className="absolute inset-0 rounded-full"
                              style={{
                                background: `conic-gradient(${
                                  score >= 80
                                    ? "#10b981"
                                    : score >= 60
                                    ? "#f59e0b"
                                    : score >= 40
                                    ? "#f97316"
                                    : "#ef4444"
                                } ${score * 3.6}deg, transparent 0deg)`,
                                opacity: 0.15,
                              }}
                            />
                            <span
                              className={`text-xs font-bold ${getScoreColor(
                                score
                              )} relative z-10`}
                            >
                              {Math.round(score)}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Price and link */}
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-semibold">
                          {result
                            ? formatPrice(result.price, result.currency)
                            : "N/A"}
                        </span>
                        {result?.product_url && (
                          <a
                            href={result.product_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-primary hover:underline flex items-center gap-1"
                          >
                            View listing
                            <ExternalLink className="size-3" />
                          </a>
                        )}
                      </div>

                      {/* Notes */}
                      {item.notes && (
                        <div className="bg-secondary/50 rounded-md p-2.5">
                          <p className="text-xs text-muted-foreground leading-relaxed">
                            <StickyNote className="size-3 inline mr-1 -mt-0.5" />
                            {item.notes}
                          </p>
                        </div>
                      )}

                      {/* Action buttons */}
                      <div className="flex items-center gap-1.5 pt-1 flex-wrap">
                        {/* Status transition buttons */}
                        {item.status !== "imported" && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-xs"
                            disabled={updatingId === item.id}
                            onClick={() =>
                              handleStatusUpdate(item.id, "imported")
                            }
                          >
                            {updatingId === item.id ? (
                              <Loader2 className="size-3 animate-spin" />
                            ) : (
                              <PackageCheck className="size-3" />
                            )}
                            Import
                          </Button>
                        )}
                        {item.status !== "dismissed" && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-xs"
                            disabled={updatingId === item.id}
                            onClick={() =>
                              handleStatusUpdate(item.id, "dismissed")
                            }
                          >
                            {updatingId === item.id ? (
                              <Loader2 className="size-3 animate-spin" />
                            ) : (
                              <XCircle className="size-3" />
                            )}
                            Dismiss
                          </Button>
                        )}
                        {item.status !== "watching" && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-xs"
                            disabled={updatingId === item.id}
                            onClick={() =>
                              handleStatusUpdate(item.id, "watching")
                            }
                          >
                            {updatingId === item.id ? (
                              <Loader2 className="size-3 animate-spin" />
                            ) : (
                              <Eye className="size-3" />
                            )}
                            Watch
                          </Button>
                        )}

                        {/* Notes button */}
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-xs text-muted-foreground"
                          onClick={() => openNotesEditor(item)}
                        >
                          <StickyNote className="size-3" />
                          Notes
                        </Button>

                        {/* Delete */}
                        <Button
                          variant="ghost"
                          size="icon"
                          className="ml-auto text-muted-foreground hover:text-destructive size-8"
                          disabled={deletingId === item.id}
                          onClick={() => handleDelete(item.id)}
                        >
                          {deletingId === item.id ? (
                            <Loader2 className="size-3.5 animate-spin" />
                          ) : (
                            <Trash2 className="size-3.5" />
                          )}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </StaggerChildren>

            {/* Pagination */}
            {totalPages > 1 && (
              <FadeIn delay={0.3}>
                <div className="flex items-center justify-between pt-2">
                  <p className="text-sm text-muted-foreground">
                    Showing {(page - 1) * perPage + 1}
                    {" "}-{" "}
                    {Math.min(page * perPage, total)} of {total} items
                  </p>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="icon"
                      disabled={page <= 1}
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                    >
                      <ChevronLeft className="size-4" />
                    </Button>
                    <span className="text-sm font-medium px-2">
                      {page} / {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="icon"
                      disabled={page >= totalPages}
                      onClick={() =>
                        setPage((p) => Math.min(totalPages, p + 1))
                      }
                    >
                      <ChevronRight className="size-4" />
                    </Button>
                  </div>
                </div>
              </FadeIn>
            )}
          </>
        )}

        {/* ── Notes Editing Dialog ── */}
        <Dialog
          open={editingNotesId !== null}
          onOpenChange={(open) => {
            if (!open) setEditingNotesId(null);
          }}
        >
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <StickyNote className="size-5" />
                Edit Notes
              </DialogTitle>
              <DialogDescription>
                Add or update your notes for this product.
              </DialogDescription>
            </DialogHeader>

            <div className="py-2">
              <Input
                placeholder="e.g., Great margins, low competition, trending on TikTok..."
                value={notesInput}
                onChange={(e) => setNotesInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleSaveNotes();
                  }
                }}
              />
              <p className="text-xs text-muted-foreground mt-2">
                Notes help you remember why this product caught your attention.
              </p>
            </div>

            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline">Cancel</Button>
              </DialogClose>
              <Button onClick={handleSaveNotes} disabled={savingNotes}>
                {savingNotes ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  "Save Notes"
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageTransition>
    </Shell>
  );
}
