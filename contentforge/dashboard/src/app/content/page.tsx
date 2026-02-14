/**
 * Content generation history and creation page.
 *
 * Displays a paginated table of past generation jobs with status badges,
 * content type counts, and creation dates. Users can create new generation
 * jobs via a dialog form that accepts manual product data or a URL.
 *
 * **For Developers:**
 *   - Fetches from `GET /api/v1/content/jobs?page=N&per_page=20` on mount and pagination.
 *   - Creates jobs via `POST /api/v1/content/generate` with source_data and content_types.
 *   - Deletes jobs via `DELETE /api/v1/content/jobs/{id}`.
 *   - Uses Shell wrapper, motion animations, and the standard Card/Badge/Button components.
 *   - The "New Generation" dialog collects product name, price, category, features, and
 *     lets the user select which content types to generate.
 *
 * **For Project Managers:**
 *   - This is the primary history page where users track all their generation jobs.
 *   - The "New Generation" button is the main CTA — it should be prominent and intuitive.
 *   - Each row links to the full job detail (expandable in-place).
 *
 * **For QA Engineers:**
 *   - Verify loading skeletons display before data arrives.
 *   - Test with zero jobs (new account) — should show empty state.
 *   - Test creating a job via the dialog — verify it appears at the top of the list.
 *   - Test deleting a job — verify it disappears from the list.
 *   - Test pagination — verify next/previous buttons and page count.
 *   - Verify status badges are correctly colored (completed=green, failed=red, pending=yellow).
 *
 * **For End Users:**
 *   - View all your past content generation jobs in one place.
 *   - Click "New Generation" to create AI content for a new product.
 *   - Expand a job to see all generated content, copy to clipboard, or edit.
 *   - Delete jobs you no longer need.
 */

"use client";

import * as React from "react";
import {
  Sparkles,
  Trash2,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Loader2,
  Plus,
  Clock,
  FileText,
  Image as ImageIcon,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
} from "lucide-react";
import { Shell } from "@/components/shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { FadeIn, StaggerChildren, PageTransition } from "@/components/motion";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

/* ── Type Definitions ─────────────────────────────────────────────── */

/** Shape of a single generated content item within a job. */
interface ContentItem {
  id: string;
  content_type: string;
  content: string;
  word_count: number;
  version: number;
}

/** Shape of a single image item within a job. */
interface ImageItem {
  id: string;
  original_url: string;
  optimized_url: string | null;
  format: string;
  status: string;
}

/** Shape of a generation job from the API. */
interface GenerationJob {
  id: string;
  source_url: string | null;
  source_type: string;
  source_data: Record<string, unknown>;
  status: string;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  content_items: ContentItem[];
  image_items: ImageItem[];
}

/** Shape of the paginated jobs response. */
interface PaginatedJobs {
  items: GenerationJob[];
  total: number;
  page: number;
  per_page: number;
}

/** Available content types for generation. */
const CONTENT_TYPES = [
  { key: "title", label: "Title" },
  { key: "description", label: "Description" },
  { key: "meta_description", label: "Meta Description" },
  { key: "keywords", label: "Keywords" },
  { key: "bullet_points", label: "Bullet Points" },
] as const;

/* ── Helper Functions ─────────────────────────────────────────────── */

/**
 * Map a job status string to a Badge variant for consistent color coding.
 *
 * @param status - The generation job status (pending, processing, completed, failed).
 * @returns The Badge variant string.
 */
function statusVariant(
  status: string
): "success" | "destructive" | "secondary" | "default" {
  switch (status) {
    case "completed":
      return "success";
    case "failed":
      return "destructive";
    case "processing":
      return "default";
    default:
      return "secondary";
  }
}

/**
 * Format an ISO date string to a human-readable local date and time.
 *
 * @param iso - ISO 8601 date string.
 * @returns Formatted date string (e.g., "Jan 15, 2026, 2:30 PM").
 */
function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/* ── Main Component ───────────────────────────────────────────────── */

/**
 * Content generation history page component.
 *
 * Renders a paginated list of generation jobs with expand/collapse detail,
 * a "New Generation" dialog for creating jobs, and inline delete actions.
 *
 * @returns The content page wrapped in the Shell layout.
 */
export default function ContentPage() {
  /* ── State ── */
  const [jobs, setJobs] = React.useState<GenerationJob[]>([]);
  const [total, setTotal] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [expandedId, setExpandedId] = React.useState<string | null>(null);
  const [copiedId, setCopiedId] = React.useState<string | null>(null);
  const [deletingId, setDeletingId] = React.useState<string | null>(null);

  /* Dialog state */
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [formName, setFormName] = React.useState("");
  const [formPrice, setFormPrice] = React.useState("");
  const [formCategory, setFormCategory] = React.useState("");
  const [formFeatures, setFormFeatures] = React.useState("");
  const [formUrl, setFormUrl] = React.useState("");
  const [selectedTypes, setSelectedTypes] = React.useState<string[]>(
    CONTENT_TYPES.map((t) => t.key)
  );
  const [creating, setCreating] = React.useState(false);

  const perPage = 20;
  const totalPages = Math.ceil(total / perPage);

  /* ── Data Fetching ── */

  /**
   * Fetch the current page of generation jobs from the API.
   * Updates jobs, total, loading, and error state.
   */
  const fetchJobs = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    const { data, error: apiError } = await api.get<PaginatedJobs>(
      `/api/v1/content/jobs?page=${page}&per_page=${perPage}`
    );
    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setJobs(data.items);
      setTotal(data.total);
    }
    setLoading(false);
  }, [page]);

  React.useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  /* ── Actions ── */

  /**
   * Create a new generation job from the dialog form data.
   * On success, closes the dialog, resets the form, and refreshes the list.
   */
  async function handleCreate() {
    if (!formName.trim()) return;
    setCreating(true);

    const sourceData: Record<string, unknown> = { name: formName.trim() };
    if (formPrice.trim()) sourceData.price = formPrice.trim();
    if (formCategory.trim()) sourceData.category = formCategory.trim();
    if (formFeatures.trim()) {
      sourceData.features = formFeatures
        .split(",")
        .map((f) => f.trim())
        .filter(Boolean);
    }

    const body: Record<string, unknown> = {
      source_type: formUrl.trim() ? "url" : "manual",
      source_data: sourceData,
      content_types: selectedTypes,
    };
    if (formUrl.trim()) body.source_url = formUrl.trim();

    const { error: apiError } = await api.post<GenerationJob>(
      "/api/v1/content/generate",
      body
    );

    setCreating(false);
    if (apiError) {
      setError(apiError.message);
      return;
    }

    /* Reset form and refresh */
    setDialogOpen(false);
    setFormName("");
    setFormPrice("");
    setFormCategory("");
    setFormFeatures("");
    setFormUrl("");
    setSelectedTypes(CONTENT_TYPES.map((t) => t.key));
    setPage(1);
    fetchJobs();
  }

  /**
   * Delete a generation job by ID.
   * On success, refreshes the job list.
   *
   * @param jobId - The UUID of the job to delete.
   */
  async function handleDelete(jobId: string) {
    setDeletingId(jobId);
    const { error: apiError } = await api.del(`/api/v1/content/jobs/${jobId}`);
    setDeletingId(null);
    if (apiError) {
      setError(apiError.message);
      return;
    }
    fetchJobs();
  }

  /**
   * Copy a content item's text to the clipboard.
   * Shows a brief "copied" indicator on the corresponding button.
   *
   * @param contentId - The content item's ID (used for the copied indicator).
   * @param text - The text to copy to clipboard.
   */
  async function handleCopy(contentId: string, text: string) {
    await navigator.clipboard.writeText(text);
    setCopiedId(contentId);
    setTimeout(() => setCopiedId(null), 1500);
  }

  /**
   * Toggle a content type in the selected types list.
   *
   * @param typeKey - The content type key to toggle.
   */
  function toggleType(typeKey: string) {
    setSelectedTypes((prev) =>
      prev.includes(typeKey)
        ? prev.filter((t) => t !== typeKey)
        : [...prev, typeKey]
    );
  }

  /* ── Render ── */
  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* ── Page Header ── */}
        <FadeIn direction="down">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight">
                Content Generation
              </h2>
              <p className="text-muted-foreground mt-1">
                Generate AI-optimized product content and track your history.
              </p>
            </div>
            <Button onClick={() => setDialogOpen(true)}>
              <Plus className="size-4" />
              New Generation
            </Button>
          </div>
        </FadeIn>

        {/* ── Loading Skeletons ── */}
        {loading ? (
          <div className="space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <Card key={i}>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div className="space-y-2">
                      <Skeleton className="h-5 w-48" />
                      <Skeleton className="h-4 w-32" />
                    </div>
                    <Skeleton className="h-6 w-20 rounded-full" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : error && jobs.length === 0 ? (
          /* ── Error State ── */
          <FadeIn>
            <Card className="border-destructive/50">
              <CardContent className="pt-6 flex items-start gap-3">
                <AlertCircle className="size-5 text-destructive shrink-0 mt-0.5" />
                <div>
                  <p className="text-destructive text-sm font-medium">
                    Failed to load generation history
                  </p>
                  <p className="text-destructive/80 text-sm mt-1">{error}</p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-3"
                    onClick={() => fetchJobs()}
                  >
                    Retry
                  </Button>
                </div>
              </CardContent>
            </Card>
          </FadeIn>
        ) : jobs.length === 0 ? (
          /* ── Empty State ── */
          <FadeIn>
            <Card>
              <CardContent className="pt-6 text-center py-16">
                <Sparkles className="size-12 text-muted-foreground/40 mx-auto mb-4" />
                <h3 className="font-heading text-lg font-semibold">
                  No generations yet
                </h3>
                <p className="text-muted-foreground text-sm mt-1 max-w-md mx-auto">
                  Create your first AI content generation to see it appear here.
                  Enter product details or a URL and let AI craft optimized content.
                </p>
                <Button className="mt-6" onClick={() => setDialogOpen(true)}>
                  <Sparkles className="size-4" />
                  Generate Your First Content
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        ) : (
          /* ── Job List ── */
          <>
            <StaggerChildren className="space-y-4" staggerDelay={0.06}>
              {jobs.map((job) => {
                const isExpanded = expandedId === job.id;
                const productName =
                  (job.source_data?.name as string) ||
                  job.source_url ||
                  "Untitled Product";

                return (
                  <Card key={job.id} className="overflow-hidden">
                    {/* Job summary row */}
                    <button
                      type="button"
                      className="w-full text-left px-6 pt-5 pb-4 flex items-center justify-between hover:bg-secondary/30 transition-colors"
                      onClick={() =>
                        setExpandedId(isExpanded ? null : job.id)
                      }
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-3 flex-wrap">
                          <span className="font-heading font-semibold truncate">
                            {productName}
                          </span>
                          <Badge variant={statusVariant(job.status)}>
                            {job.status}
                          </Badge>
                          <span className="text-xs text-muted-foreground capitalize">
                            {job.source_type}
                          </span>
                        </div>
                        <div className="flex items-center gap-4 mt-1.5 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <FileText className="size-3.5" />
                            {job.content_items.length} content
                          </span>
                          {job.image_items.length > 0 && (
                            <span className="flex items-center gap-1">
                              <ImageIcon className="size-3.5" />
                              {job.image_items.length} images
                            </span>
                          )}
                          <span className="flex items-center gap-1">
                            <Clock className="size-3.5" />
                            {formatDate(job.created_at)}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0 ml-4">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-muted-foreground hover:text-destructive"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDelete(job.id);
                          }}
                          disabled={deletingId === job.id}
                        >
                          {deletingId === job.id ? (
                            <Loader2 className="size-4 animate-spin" />
                          ) : (
                            <Trash2 className="size-4" />
                          )}
                        </Button>
                        {isExpanded ? (
                          <ChevronUp className="size-5 text-muted-foreground" />
                        ) : (
                          <ChevronDown className="size-5 text-muted-foreground" />
                        )}
                      </div>
                    </button>

                    {/* Expanded content detail */}
                    {isExpanded && (
                      <div className="border-t px-6 py-5 space-y-4 bg-secondary/10">
                        {job.error_message && (
                          <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3 text-sm text-destructive">
                            {job.error_message}
                          </div>
                        )}

                        {job.content_items.length === 0 ? (
                          <p className="text-sm text-muted-foreground italic">
                            No content generated.
                          </p>
                        ) : (
                          <div className="grid gap-4">
                            {job.content_items.map((item) => (
                              <div
                                key={item.id}
                                className="rounded-lg border bg-card p-4 space-y-2"
                              >
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-2">
                                    <Badge variant="outline" className="capitalize text-xs">
                                      {item.content_type.replace("_", " ")}
                                    </Badge>
                                    <span className="text-xs text-muted-foreground">
                                      {item.word_count} words
                                    </span>
                                  </div>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleCopy(item.id, item.content)}
                                  >
                                    {copiedId === item.id ? (
                                      <>
                                        <Check className="size-3.5 text-emerald-500" />
                                        Copied
                                      </>
                                    ) : (
                                      <>
                                        <Copy className="size-3.5" />
                                        Copy
                                      </>
                                    )}
                                  </Button>
                                </div>
                                <p className="text-sm whitespace-pre-wrap leading-relaxed">
                                  {item.content}
                                </p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </Card>
                );
              })}
            </StaggerChildren>

            {/* ── Pagination ── */}
            {totalPages > 1 && (
              <FadeIn delay={0.2}>
                <div className="flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">
                    Showing {(page - 1) * perPage + 1}–
                    {Math.min(page * perPage, total)} of {total} jobs
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
          </>
        )}

        {/* ── Inline Error Toast ── */}
        {error && jobs.length > 0 && (
          <FadeIn>
            <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          </FadeIn>
        )}

        {/* ── New Generation Dialog ── */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="font-heading">
                New Content Generation
              </DialogTitle>
              <DialogDescription>
                Enter product details to generate AI-optimized content.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2">
              {/* Product URL (optional) */}
              <div className="space-y-1.5">
                <label
                  htmlFor="gen-url"
                  className="text-sm font-medium"
                >
                  Product URL
                  <span className="text-muted-foreground font-normal ml-1">(optional)</span>
                </label>
                <Input
                  id="gen-url"
                  placeholder="https://example.com/product/..."
                  value={formUrl}
                  onChange={(e) => setFormUrl(e.target.value)}
                />
              </div>

              {/* Product Name */}
              <div className="space-y-1.5">
                <label
                  htmlFor="gen-name"
                  className="text-sm font-medium"
                >
                  Product Name <span className="text-destructive">*</span>
                </label>
                <Input
                  id="gen-name"
                  placeholder="e.g. Wireless Bluetooth Headphones"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                />
              </div>

              {/* Price and Category side-by-side */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label
                    htmlFor="gen-price"
                    className="text-sm font-medium"
                  >
                    Price
                  </label>
                  <Input
                    id="gen-price"
                    placeholder="29.99"
                    value={formPrice}
                    onChange={(e) => setFormPrice(e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <label
                    htmlFor="gen-category"
                    className="text-sm font-medium"
                  >
                    Category
                  </label>
                  <Input
                    id="gen-category"
                    placeholder="Electronics"
                    value={formCategory}
                    onChange={(e) => setFormCategory(e.target.value)}
                  />
                </div>
              </div>

              {/* Features */}
              <div className="space-y-1.5">
                <label
                  htmlFor="gen-features"
                  className="text-sm font-medium"
                >
                  Features
                  <span className="text-muted-foreground font-normal ml-1">(comma-separated)</span>
                </label>
                <Input
                  id="gen-features"
                  placeholder="Noise cancelling, 30hr battery, Lightweight"
                  value={formFeatures}
                  onChange={(e) => setFormFeatures(e.target.value)}
                />
              </div>

              {/* Content Types */}
              <div className="space-y-2">
                <span className="text-sm font-medium">Content Types</span>
                <div className="flex flex-wrap gap-2">
                  {CONTENT_TYPES.map((ct) => {
                    const isSelected = selectedTypes.includes(ct.key);
                    return (
                      <button
                        key={ct.key}
                        type="button"
                        onClick={() => toggleType(ct.key)}
                        className={cn(
                          "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                          isSelected
                            ? "bg-primary text-primary-foreground border-primary"
                            : "bg-background text-muted-foreground border-input hover:bg-secondary"
                        )}
                      >
                        {ct.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setDialogOpen(false)}
                disabled={creating}
              >
                Cancel
              </Button>
              <Button
                onClick={handleCreate}
                disabled={creating || !formName.trim() || selectedTypes.length === 0}
              >
                {creating ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Sparkles className="size-4" />
                )}
                Generate
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageTransition>
    </Shell>
  );
}
