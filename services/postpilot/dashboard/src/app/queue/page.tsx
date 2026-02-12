/**
 * Queue page — AI-powered content generation queue with calendar view.
 *
 * Displays the content generation queue with product cards, AI caption
 * generation controls, and an approval/rejection workflow. Includes a
 * mini calendar view showing upcoming scheduled content.
 *
 * **For Developers:**
 *   - Fetches queue items from `GET /api/v1/queue` with page, per_page, status params.
 *   - Create uses `POST /api/v1/queue` with product_data and platforms.
 *   - Generate caption uses `POST /api/v1/queue/{id}/generate`.
 *   - Approve/Reject use `POST /api/v1/queue/{id}/approve` and `POST /api/v1/queue/{id}/reject`.
 *   - Delete uses `DELETE /api/v1/queue/{id}`.
 *   - Calendar sidebar fetches from `GET /api/v1/posts/calendar`.
 *   - Motion animations for card entrance and state transitions.
 *
 * **For Project Managers:**
 *   - The queue is the content automation engine. Users add products, AI generates
 *     captions, and users review before scheduling. This reduces time-to-publish.
 *   - The calendar sidebar gives a quick view of scheduled content density.
 *
 * **For QA Engineers:**
 *   - Verify loading skeletons during fetch.
 *   - Test add-to-queue flow with product data.
 *   - Test AI generation button populates the caption field.
 *   - Test approve and reject transitions.
 *   - Test delete for pending/rejected items (should work) vs approved (should fail).
 *   - Verify calendar sidebar shows correct scheduled post counts per day.
 *   - Test empty state when queue has no items.
 *
 * **For End Users:**
 *   - Add products to your content queue and let AI generate engaging captions.
 *   - Review generated captions, approve the good ones, and reject the rest.
 *   - The calendar shows when your scheduled posts will go live.
 */

"use client";

import * as React from "react";
import {
  Plus,
  Sparkles,
  CheckCircle2,
  XCircle,
  Trash2,
  Package,
  ListOrdered,
  Calendar,
  Clock,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Filter,
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
import { FadeIn, StaggerChildren, PageTransition, AnimatedCounter } from "@/components/motion";
import { api } from "@/lib/api";

/** Shape of a queue item returned by the API. */
interface QueueItem {
  id: string;
  product_data: {
    title?: string;
    description?: string;
    price?: number;
    image_url?: string;
    category?: string;
    [key: string]: unknown;
  };
  ai_generated_content: string | null;
  platforms: string[];
  status: "pending" | "approved" | "rejected" | "posted";
  created_at: string;
  updated_at: string;
}

/** Paginated queue list from the API. */
interface QueueListResponse {
  items: QueueItem[];
  total: number;
  page: number;
  per_page: number;
}

/** Calendar day from the posts calendar API. */
interface CalendarDay {
  date: string;
  posts: Array<{ id: string; content: string; platform: string; status: string }>;
}

/** Calendar view from the API. */
interface CalendarView {
  days: CalendarDay[];
  total_posts: number;
}

/** Status filter options. */
const QUEUE_STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "pending", label: "Pending" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "posted", label: "Posted" },
] as const;

/**
 * Map queue status to a badge variant and color.
 *
 * @param status - The queue item lifecycle status.
 * @returns Object with badge variant and label.
 */
function getQueueStatusDisplay(status: QueueItem["status"]) {
  switch (status) {
    case "pending":
      return { variant: "secondary" as const, label: "Pending Review" };
    case "approved":
      return { variant: "success" as const, label: "Approved" };
    case "rejected":
      return { variant: "destructive" as const, label: "Rejected" };
    case "posted":
      return { variant: "default" as const, label: "Posted" };
  }
}

/**
 * Queue page component.
 *
 * @returns The content queue page wrapped in the Shell layout.
 */
export default function QueuePage() {
  /* ── Queue state ── */
  const [items, setItems] = React.useState<QueueItem[]>([]);
  const [total, setTotal] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [statusFilter, setStatusFilter] = React.useState("");
  const perPage = 10;

  /* Calendar sidebar state */
  const [calendarDays, setCalendarDays] = React.useState<CalendarDay[]>([]);
  const [calendarTotal, setCalendarTotal] = React.useState(0);
  const [calendarLoading, setCalendarLoading] = React.useState(true);

  /* Add item dialog state */
  const [addOpen, setAddOpen] = React.useState(false);
  const [productTitle, setProductTitle] = React.useState("");
  const [productDescription, setProductDescription] = React.useState("");
  const [productPrice, setProductPrice] = React.useState("");
  const [productImageUrl, setProductImageUrl] = React.useState("");
  const [targetPlatforms, setTargetPlatforms] = React.useState<string[]>(["instagram"]);
  const [adding, setAdding] = React.useState(false);

  /* Generating captions state (tracks which item ID is generating) */
  const [generatingId, setGeneratingId] = React.useState<string | null>(null);

  /**
   * Fetch queue items from the API with current filters and pagination.
   */
  const fetchQueue = React.useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams({
      page: String(page),
      per_page: String(perPage),
    });
    if (statusFilter) params.set("status", statusFilter);

    const { data, error: apiError } = await api.get<QueueListResponse>(
      `/api/v1/queue?${params}`
    );
    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setItems(data.items);
      setTotal(data.total);
      setError(null);
    }
    setLoading(false);
  }, [page, statusFilter]);

  /**
   * Fetch the upcoming 14 days of scheduled posts for the calendar sidebar.
   */
  const fetchCalendar = React.useCallback(async () => {
    setCalendarLoading(true);
    const today = new Date();
    const twoWeeksOut = new Date(today);
    twoWeeksOut.setDate(twoWeeksOut.getDate() + 14);

    const start = today.toISOString().split("T")[0];
    const end = twoWeeksOut.toISOString().split("T")[0];

    const { data } = await api.get<CalendarView>(
      `/api/v1/posts/calendar?start_date=${start}&end_date=${end}`
    );
    if (data) {
      setCalendarDays(data.days);
      setCalendarTotal(data.total_posts);
    }
    setCalendarLoading(false);
  }, []);

  React.useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  React.useEffect(() => {
    fetchCalendar();
  }, [fetchCalendar]);

  /**
   * Add a new product to the content queue.
   */
  async function handleAdd() {
    if (!productTitle.trim()) return;
    setAdding(true);

    const productData: Record<string, unknown> = {
      title: productTitle.trim(),
    };
    if (productDescription.trim()) productData.description = productDescription.trim();
    if (productPrice.trim()) productData.price = parseFloat(productPrice) || 0;
    if (productImageUrl.trim()) productData.image_url = productImageUrl.trim();

    const { error: apiError } = await api.post<QueueItem>("/api/v1/queue", {
      product_data: productData,
      platforms: targetPlatforms,
    });

    if (apiError) {
      setError(apiError.message);
    } else {
      setProductTitle("");
      setProductDescription("");
      setProductPrice("");
      setProductImageUrl("");
      setTargetPlatforms(["instagram"]);
      setAddOpen(false);
      await fetchQueue();
    }
    setAdding(false);
  }

  /**
   * Generate AI caption for a specific queue item.
   *
   * @param itemId - UUID of the queue item.
   */
  async function handleGenerate(itemId: string) {
    setGeneratingId(itemId);
    const { error: apiError } = await api.post<QueueItem>(
      `/api/v1/queue/${itemId}/generate`
    );
    if (apiError) {
      setError(apiError.message);
    } else {
      await fetchQueue();
    }
    setGeneratingId(null);
  }

  /**
   * Approve a queue item for scheduling.
   *
   * @param itemId - UUID of the queue item.
   */
  async function handleApprove(itemId: string) {
    const { error: apiError } = await api.post<QueueItem>(
      `/api/v1/queue/${itemId}/approve`
    );
    if (apiError) {
      setError(apiError.message);
    } else {
      await fetchQueue();
    }
  }

  /**
   * Reject a queue item.
   *
   * @param itemId - UUID of the queue item.
   */
  async function handleReject(itemId: string) {
    const { error: apiError } = await api.post<QueueItem>(
      `/api/v1/queue/${itemId}/reject`
    );
    if (apiError) {
      setError(apiError.message);
    } else {
      await fetchQueue();
    }
  }

  /**
   * Delete a queue item permanently.
   *
   * @param itemId - UUID of the queue item.
   */
  async function handleDelete(itemId: string) {
    const { error: apiError } = await api.del(`/api/v1/queue/${itemId}`);
    if (apiError) {
      setError(apiError.message);
    } else {
      await fetchQueue();
    }
  }

  /**
   * Toggle a platform in the target platforms list for the add dialog.
   *
   * @param platform - The platform to toggle.
   */
  function togglePlatform(platform: string) {
    setTargetPlatforms((prev) =>
      prev.includes(platform)
        ? prev.filter((p) => p !== platform)
        : [...prev, platform]
    );
  }

  /** Total number of pages. */
  const totalPages = Math.max(1, Math.ceil(total / perPage));

  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* ── Page Header ── */}
        <FadeIn direction="down">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight">
                Content Queue
              </h2>
              <p className="text-muted-foreground mt-1">
                Add products, generate AI captions, and approve for scheduling
              </p>
            </div>
            <Button onClick={() => setAddOpen(true)}>
              <Plus className="size-4" />
              Add to Queue
            </Button>
          </div>
        </FadeIn>

        {/* ── Main Layout: Queue + Calendar Sidebar ── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Queue items (2/3 width) */}
          <div className="lg:col-span-2 space-y-6">
            {/* Stats row */}
            <FadeIn delay={0.1}>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <Card>
                  <CardContent className="pt-4 pb-4">
                    <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
                      In Queue
                    </p>
                    <AnimatedCounter
                      value={total}
                      className="text-xl font-bold font-heading block mt-0.5"
                    />
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4 pb-4">
                    <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
                      Pending
                    </p>
                    <AnimatedCounter
                      value={items.filter((i) => i.status === "pending").length}
                      className="text-xl font-bold font-heading block mt-0.5"
                    />
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4 pb-4">
                    <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
                      Approved
                    </p>
                    <AnimatedCounter
                      value={items.filter((i) => i.status === "approved").length}
                      className="text-xl font-bold font-heading block mt-0.5"
                    />
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4 pb-4">
                    <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
                      Rejected
                    </p>
                    <AnimatedCounter
                      value={items.filter((i) => i.status === "rejected").length}
                      className="text-xl font-bold font-heading block mt-0.5"
                    />
                  </CardContent>
                </Card>
              </div>
            </FadeIn>

            {/* Filters */}
            <FadeIn delay={0.15}>
              <div className="flex items-center gap-3">
                <Filter className="size-4 text-muted-foreground" />
                <select
                  value={statusFilter}
                  onChange={(e) => {
                    setStatusFilter(e.target.value);
                    setPage(1);
                  }}
                  className="h-9 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {QUEUE_STATUS_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            </FadeIn>

            {/* Error state */}
            {error && (
              <FadeIn>
                <Card className="border-destructive/50">
                  <CardContent className="pt-6">
                    <p className="text-destructive text-sm">{error}</p>
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-3"
                      onClick={() => {
                        setError(null);
                        fetchQueue();
                      }}
                    >
                      <RefreshCw className="size-3.5" />
                      Retry
                    </Button>
                  </CardContent>
                </Card>
              </FadeIn>
            )}

            {/* Loading state */}
            {loading ? (
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Card key={i}>
                    <CardContent className="pt-6">
                      <div className="flex gap-4">
                        <Skeleton className="size-16 rounded-lg shrink-0" />
                        <div className="flex-1 space-y-2">
                          <Skeleton className="h-4 w-2/3" />
                          <Skeleton className="h-3 w-full" />
                          <Skeleton className="h-3 w-1/2" />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : items.length === 0 ? (
              /* Empty state */
              <FadeIn delay={0.2}>
                <Card>
                  <CardContent className="pt-6">
                    <div className="flex flex-col items-center justify-center py-12 text-center">
                      <div className="flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
                        <ListOrdered className="size-7 text-muted-foreground" />
                      </div>
                      <h3 className="font-heading text-lg font-semibold mb-1">
                        Queue is empty
                      </h3>
                      <p className="text-muted-foreground text-sm max-w-sm mb-6">
                        Add products to the queue and let AI generate engaging
                        social media captions for you.
                      </p>
                      <Button onClick={() => setAddOpen(true)}>
                        <Plus className="size-4" />
                        Add Your First Product
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </FadeIn>
            ) : (
              /* Queue item cards */
              <StaggerChildren className="space-y-3" staggerDelay={0.06}>
                {items.map((item) => {
                  const statusDisplay = getQueueStatusDisplay(item.status);
                  const isGenerating = generatingId === item.id;

                  return (
                    <Card
                      key={item.id}
                      className="hover:shadow-md transition-shadow duration-200"
                    >
                      <CardContent className="pt-6">
                        <div className="flex gap-4">
                          {/* Product image or placeholder */}
                          {item.product_data.image_url ? (
                            <img
                              src={item.product_data.image_url as string}
                              alt={item.product_data.title as string ?? "Product"}
                              className="size-16 rounded-lg object-cover shrink-0 bg-muted"
                            />
                          ) : (
                            <div className="flex items-center justify-center size-16 rounded-lg bg-muted shrink-0">
                              <Package className="size-6 text-muted-foreground" />
                            </div>
                          )}

                          {/* Product info */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-start justify-between gap-2">
                              <div>
                                <h4 className="font-medium text-sm line-clamp-1">
                                  {item.product_data.title ?? "Untitled Product"}
                                </h4>
                                {item.product_data.price !== undefined && (
                                  <p className="text-xs text-muted-foreground mt-0.5">
                                    ${Number(item.product_data.price).toFixed(2)}
                                  </p>
                                )}
                              </div>
                              <Badge variant={statusDisplay.variant}>
                                {statusDisplay.label}
                              </Badge>
                            </div>

                            {/* Platforms */}
                            <div className="flex gap-1.5 mt-2">
                              {item.platforms.map((platform) => (
                                <span
                                  key={platform}
                                  className="text-xs px-2 py-0.5 rounded-full bg-muted capitalize"
                                >
                                  {platform}
                                </span>
                              ))}
                            </div>

                            {/* AI Generated Content */}
                            {item.ai_generated_content && (
                              <div className="mt-3 p-3 rounded-lg bg-muted/50 border border-muted">
                                <p className="text-xs text-muted-foreground font-medium mb-1 flex items-center gap-1">
                                  <Sparkles className="size-3" />
                                  AI Generated Caption
                                </p>
                                <p className="text-sm line-clamp-3 whitespace-pre-line">
                                  {item.ai_generated_content}
                                </p>
                              </div>
                            )}

                            {/* Actions */}
                            <div className="flex flex-wrap items-center gap-2 mt-3">
                              {item.status === "pending" && (
                                <>
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    disabled={isGenerating}
                                    onClick={() => handleGenerate(item.id)}
                                  >
                                    <Sparkles className="size-3.5" />
                                    {isGenerating
                                      ? "Generating..."
                                      : item.ai_generated_content
                                        ? "Regenerate"
                                        : "Generate Caption"}
                                  </Button>
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    className="text-emerald-600 border-emerald-200 hover:bg-emerald-50 hover:text-emerald-700"
                                    onClick={() => handleApprove(item.id)}
                                  >
                                    <CheckCircle2 className="size-3.5" />
                                    Approve
                                  </Button>
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    className="text-destructive border-destructive/30 hover:bg-destructive/10"
                                    onClick={() => handleReject(item.id)}
                                  >
                                    <XCircle className="size-3.5" />
                                    Reject
                                  </Button>
                                </>
                              )}
                              {(item.status === "pending" ||
                                item.status === "rejected") && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="text-destructive hover:text-destructive hover:bg-destructive/10"
                                  onClick={() => handleDelete(item.id)}
                                >
                                  <Trash2 className="size-3.5" />
                                  Delete
                                </Button>
                              )}
                            </div>

                            {/* Timestamp */}
                            <p className="text-xs text-muted-foreground mt-2">
                              Added {new Date(item.created_at).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </StaggerChildren>
            )}

            {/* Pagination */}
            {total > perPage && (
              <FadeIn delay={0.3}>
                <div className="flex items-center justify-between pt-2">
                  <p className="text-sm text-muted-foreground">
                    Showing {(page - 1) * perPage + 1}–
                    {Math.min(page * perPage, total)} of {total} items
                  </p>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page <= 1}
                      onClick={() => setPage((p) => p - 1)}
                    >
                      <ChevronLeft className="size-4" />
                      Previous
                    </Button>
                    <span className="text-sm text-muted-foreground px-2">
                      Page {page} of {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page >= totalPages}
                      onClick={() => setPage((p) => p + 1)}
                    >
                      Next
                      <ChevronRight className="size-4" />
                    </Button>
                  </div>
                </div>
              </FadeIn>
            )}
          </div>

          {/* Right: Calendar Sidebar (1/3 width) */}
          <div className="space-y-4">
            <FadeIn delay={0.2}>
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Calendar className="size-4 text-muted-foreground" />
                    Upcoming Schedule
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {calendarLoading ? (
                    <div className="space-y-3">
                      {Array.from({ length: 5 }).map((_, i) => (
                        <div key={i} className="flex items-center gap-3">
                          <Skeleton className="h-8 w-8 rounded" />
                          <Skeleton className="h-4 flex-1" />
                        </div>
                      ))}
                    </div>
                  ) : calendarDays.length === 0 ? (
                    <div className="text-center py-6">
                      <Clock className="size-8 text-muted-foreground mx-auto mb-2" />
                      <p className="text-sm text-muted-foreground">
                        No scheduled posts in the next 14 days
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {calendarDays.map((day) => {
                        const date = new Date(day.date + "T00:00:00");
                        const dayNum = date.getDate();
                        const dayName = date.toLocaleDateString("en-US", {
                          weekday: "short",
                        });
                        const monthName = date.toLocaleDateString("en-US", {
                          month: "short",
                        });

                        return (
                          <div
                            key={day.date}
                            className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50 transition-colors"
                          >
                            <div className="flex flex-col items-center justify-center size-10 rounded-lg bg-primary/10 shrink-0">
                              <span className="text-[10px] font-medium text-primary leading-none">
                                {dayName}
                              </span>
                              <span className="text-sm font-bold text-primary leading-tight">
                                {dayNum}
                              </span>
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium">
                                {monthName} {dayNum}
                              </p>
                              <p className="text-xs text-muted-foreground">
                                {day.posts.length} post
                                {day.posts.length !== 1 ? "s" : ""} scheduled
                              </p>
                            </div>
                            <Badge variant="secondary" className="shrink-0">
                              {day.posts.length}
                            </Badge>
                          </div>
                        );
                      })}
                      <div className="pt-2 border-t mt-2">
                        <p className="text-xs text-muted-foreground text-center">
                          {calendarTotal} total scheduled in next 14 days
                        </p>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </FadeIn>
          </div>
        </div>

        {/* ── Add to Queue Dialog ── */}
        <Dialog open={addOpen} onOpenChange={setAddOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Add Product to Queue</DialogTitle>
              <DialogDescription>
                Enter product details and AI will generate captions for your selected
                platforms.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2">
              {/* Product title */}
              <div>
                <label className="text-sm font-medium mb-2 block">
                  Product Title *
                </label>
                <Input
                  value={productTitle}
                  onChange={(e) => setProductTitle(e.target.value)}
                  placeholder="Wireless Noise-Cancelling Headphones"
                />
              </div>

              {/* Product description */}
              <div>
                <label className="text-sm font-medium mb-2 block">
                  Description
                </label>
                <textarea
                  value={productDescription}
                  onChange={(e) => setProductDescription(e.target.value)}
                  placeholder="Brief product description for AI caption context..."
                  rows={3}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
                />
              </div>

              {/* Price and image URL in a row */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-sm font-medium mb-2 block">Price</label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={productPrice}
                    onChange={(e) => setProductPrice(e.target.value)}
                    placeholder="79.99"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">
                    Image URL
                  </label>
                  <Input
                    value={productImageUrl}
                    onChange={(e) => setProductImageUrl(e.target.value)}
                    placeholder="https://..."
                  />
                </div>
              </div>

              {/* Target platforms */}
              <div>
                <label className="text-sm font-medium mb-2 block">
                  Target Platforms
                </label>
                <div className="flex gap-2">
                  {["instagram", "facebook", "tiktok"].map((platform) => {
                    const isActive = targetPlatforms.includes(platform);
                    return (
                      <button
                        key={platform}
                        type="button"
                        onClick={() => togglePlatform(platform)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium border-2 transition-all duration-150 capitalize ${
                          isActive
                            ? "border-primary bg-primary/5 text-primary"
                            : "border-transparent bg-muted text-muted-foreground hover:bg-muted/80"
                        }`}
                      >
                        {platform}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline">Cancel</Button>
              </DialogClose>
              <Button
                onClick={handleAdd}
                disabled={adding || !productTitle.trim()}
              >
                {adding ? "Adding..." : "Add to Queue"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageTransition>
    </Shell>
  );
}
