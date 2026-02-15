/**
 * Import Management page — view, create, and manage product import jobs.
 *
 * This is the primary feature page for SourcePilot. Users can create
 * import jobs from AliExpress, CJ Dropshipping, or Spocket, track their
 * progress, and manage completed/failed imports.
 *
 * **For Developers:**
 *   - Fetches from `GET /api/v1/imports?skip=0&limit=20` on mount.
 *   - "New Import" dialog POSTs to `POST /api/v1/imports`.
 *   - Cancel/Retry actions call `POST /api/v1/imports/{id}/cancel` and `/retry`.
 *   - KPI summary cards show aggregated counts by status.
 *   - Uses paginated list with 20 items per page.
 *   - All state managed via useState hooks; no external state library.
 *
 * **For Project Managers:**
 *   - Core workflow: user pastes a supplier product URL, selects a store,
 *     configures markup, and submits. The backend scrapes and imports the product.
 *   - KPI cards give at-a-glance view of import health (completed vs failed).
 *   - Pagination keeps the list performant for high-volume importers.
 *
 * **For QA Engineers:**
 *   - Verify loading skeletons display before data arrives.
 *   - Test "New Import" dialog form validation (empty URL, missing store).
 *   - Verify cancel only shows for pending/running jobs.
 *   - Verify retry only shows for failed jobs.
 *   - Test pagination (next/prev buttons at boundaries).
 *   - Test with empty imports list — should show empty state message.
 *   - Check error state when API is down.
 *
 * **For End Users:**
 *   - Click "New Import" to import a product from a supplier.
 *   - Paste the product URL, pick a store, set your markup, and submit.
 *   - Track import progress with the status indicators and progress bars.
 *   - Cancel pending jobs or retry failed ones with the action buttons.
 */

"use client";

import * as React from "react";
import {
  Download,
  Plus,
  CheckCircle2,
  Loader2,
  XCircle,
  Clock,
  RotateCcw,
  Ban,
  Eye,
  ChevronLeft,
  ChevronRight,
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

/** Shape of an import job returned by the API. */
interface ImportJob {
  id: string;
  source: string;
  source_url: string;
  store_id: string;
  store_name?: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  markup_percent: number;
  tags: string[];
  product_data?: {
    title?: string;
    image_url?: string;
    price?: number;
  };
  error_message?: string;
  created_at: string;
  updated_at: string;
}

/** Paginated response shape from the imports endpoint. */
interface ImportsResponse {
  items: ImportJob[];
  total: number;
}

/** Shape of the new import form data. */
interface NewImportForm {
  source: string;
  source_url: string;
  store_id: string;
  markup_percent: number;
  tags: string;
}

/** Available supplier sources. */
const SOURCES = [
  { value: "aliexpress", label: "AliExpress" },
  { value: "cj", label: "CJ Dropshipping" },
  { value: "spocket", label: "Spocket" },
];

/** Number of items per page. */
const PAGE_SIZE = 20;

/**
 * Map an import status to a Badge variant and label.
 *
 * @param status - The import job status string.
 * @returns An object with the badge variant and display label.
 */
function getStatusBadge(status: ImportJob["status"]): {
  variant: "success" | "default" | "secondary" | "destructive";
  label: string;
} {
  switch (status) {
    case "completed":
      return { variant: "success", label: "Completed" };
    case "running":
      return { variant: "default", label: "Running" };
    case "pending":
      return { variant: "secondary", label: "Pending" };
    case "failed":
      return { variant: "destructive", label: "Failed" };
    default:
      return { variant: "secondary", label: status };
  }
}

/**
 * Get the icon component for an import job status.
 *
 * @param status - The import job status string.
 * @returns The corresponding Lucide icon component.
 */
function StatusIcon({ status }: { status: ImportJob["status"] }) {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="size-4 text-emerald-500" />;
    case "running":
      return <Loader2 className="size-4 text-primary animate-spin" />;
    case "pending":
      return <Clock className="size-4 text-muted-foreground" />;
    case "failed":
      return <XCircle className="size-4 text-destructive" />;
  }
}

/**
 * Import Management page component.
 *
 * @returns The imports page wrapped in the Shell layout.
 */
export default function ImportsPage() {
  const [jobs, setJobs] = React.useState<ImportJob[]>([]);
  const [total, setTotal] = React.useState(0);
  const [page, setPage] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);
  const [actionLoading, setActionLoading] = React.useState<string | null>(null);

  /** Form state for the "New Import" dialog. */
  const [form, setForm] = React.useState<NewImportForm>({
    source: "aliexpress",
    source_url: "",
    store_id: "",
    markup_percent: 30,
    tags: "",
  });

  /**
   * Fetch import jobs for the current page.
   * Called on mount and whenever the page changes.
   */
  const fetchJobs = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    const skip = page * PAGE_SIZE;
    const { data, error: apiError } = await api.get<ImportsResponse>(
      `/api/v1/imports?skip=${skip}&limit=${PAGE_SIZE}`
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

  /** Compute KPI summary counts from loaded jobs. */
  const kpis = React.useMemo(() => {
    const completed = jobs.filter((j) => j.status === "completed").length;
    const running = jobs.filter((j) => j.status === "running").length;
    const failed = jobs.filter((j) => j.status === "failed").length;
    return { total: total, completed, running, failed };
  }, [jobs, total]);

  /** Total number of pages for pagination. */
  const totalPages = Math.ceil(total / PAGE_SIZE);

  /**
   * Handle form field changes in the "New Import" dialog.
   *
   * @param field - The form field name.
   * @param value - The new field value.
   */
  function handleFormChange(field: keyof NewImportForm, value: string | number) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  /**
   * Submit the new import job to the API.
   * Closes the dialog on success and refreshes the list.
   */
  async function handleSubmit() {
    if (!form.source_url.trim() || !form.store_id.trim()) return;

    setSubmitting(true);
    const payload = {
      source: form.source,
      source_url: form.source_url.trim(),
      store_id: form.store_id.trim(),
      markup_percent: form.markup_percent,
      tags: form.tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
    };

    const { error: apiError } = await api.post("/api/v1/imports", payload);
    setSubmitting(false);

    if (!apiError) {
      setDialogOpen(false);
      setForm({
        source: "aliexpress",
        source_url: "",
        store_id: "",
        markup_percent: 30,
        tags: "",
      });
      fetchJobs();
    }
  }

  /**
   * Cancel a pending or running import job.
   *
   * @param jobId - The import job ID to cancel.
   */
  async function handleCancel(jobId: string) {
    setActionLoading(jobId);
    await api.post(`/api/v1/imports/${jobId}/cancel`);
    setActionLoading(null);
    fetchJobs();
  }

  /**
   * Retry a failed import job.
   *
   * @param jobId - The import job ID to retry.
   */
  async function handleRetry(jobId: string) {
    setActionLoading(jobId);
    await api.post(`/api/v1/imports/${jobId}/retry`);
    setActionLoading(null);
    fetchJobs();
  }

  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* ── Header ── */}
        <FadeIn direction="down">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight">
                Import Jobs
              </h2>
              <p className="text-muted-foreground mt-1">
                Manage your product imports from supplier platforms
              </p>
            </div>
            <Button onClick={() => setDialogOpen(true)}>
              <Plus className="size-4" />
              New Import
            </Button>
          </div>
        </FadeIn>

        {/* ── KPI Summary Cards ── */}
        {loading && jobs.length === 0 ? (
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
                  Total Imports
                </CardTitle>
                <Download className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <AnimatedCounter
                  value={kpis.total}
                  className="text-3xl font-bold font-heading"
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Completed
                </CardTitle>
                <CheckCircle2 className="size-4 text-emerald-500" />
              </CardHeader>
              <CardContent>
                <AnimatedCounter
                  value={kpis.completed}
                  className="text-3xl font-bold font-heading text-emerald-600"
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  In Progress
                </CardTitle>
                <Loader2 className="size-4 text-primary" />
              </CardHeader>
              <CardContent>
                <AnimatedCounter
                  value={kpis.running}
                  className="text-3xl font-bold font-heading text-primary"
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Failed
                </CardTitle>
                <XCircle className="size-4 text-destructive" />
              </CardHeader>
              <CardContent>
                <AnimatedCounter
                  value={kpis.failed}
                  className="text-3xl font-bold font-heading text-destructive"
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
                  Failed to load imports: {error}
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={() => fetchJobs()}
                >
                  Retry
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        )}

        {/* ── Import Job List ── */}
        {loading && jobs.length === 0 ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Card key={i}>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-4">
                    <Skeleton className="h-10 w-10 rounded" />
                    <div className="flex-1 space-y-2">
                      <Skeleton className="h-4 w-48" />
                      <Skeleton className="h-3 w-32" />
                    </div>
                    <Skeleton className="h-6 w-20 rounded-full" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : !error && jobs.length === 0 ? (
          <FadeIn>
            <Card>
              <CardContent className="pt-6 text-center py-12">
                <Download className="size-12 text-muted-foreground/40 mx-auto mb-4" />
                <h3 className="font-heading text-lg font-semibold mb-2">
                  No imports yet
                </h3>
                <p className="text-muted-foreground text-sm mb-4">
                  Start by importing your first product from a supplier.
                </p>
                <Button onClick={() => setDialogOpen(true)}>
                  <Plus className="size-4" />
                  Create Your First Import
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        ) : (
          <FadeIn delay={0.2}>
            <div className="space-y-3">
              {jobs.map((job) => {
                const badge = getStatusBadge(job.status);
                const title =
                  job.product_data?.title || job.source_url || "Untitled Import";
                const isActionable =
                  job.status === "pending" || job.status === "running";
                const isRetryable = job.status === "failed";
                const isLoadingAction = actionLoading === job.id;

                return (
                  <Card key={job.id} className="hover:border-primary/30 transition-colors">
                    <CardContent className="pt-6">
                      <div className="flex items-center gap-4">
                        {/* Status Icon */}
                        <div className="shrink-0">
                          <StatusIcon status={job.status} />
                        </div>

                        {/* Job Details */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <p className="font-medium text-sm truncate">
                              {title}
                            </p>
                            <Badge variant={badge.variant}>{badge.label}</Badge>
                          </div>
                          <div className="flex items-center gap-3 text-xs text-muted-foreground">
                            <span className="capitalize">{job.source}</span>
                            <span>&middot;</span>
                            <span>{job.store_name || job.store_id}</span>
                            <span>&middot;</span>
                            <span>
                              {new Date(job.created_at).toLocaleDateString()}
                            </span>
                          </div>

                          {/* Progress bar for running jobs */}
                          {job.status === "running" && (
                            <div className="mt-2 h-1.5 rounded-full bg-secondary overflow-hidden max-w-xs">
                              <div
                                className="h-full rounded-full bg-primary transition-all duration-500"
                                style={{ width: `${Math.min(job.progress, 100)}%` }}
                              />
                            </div>
                          )}

                          {/* Error message for failed jobs */}
                          {job.status === "failed" && job.error_message && (
                            <p className="text-xs text-destructive mt-1 truncate max-w-md">
                              {job.error_message}
                            </p>
                          )}
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-2 shrink-0">
                          <Button variant="ghost" size="icon" title="View details">
                            <Eye className="size-4" />
                          </Button>
                          {isActionable && (
                            <Button
                              variant="ghost"
                              size="icon"
                              title="Cancel import"
                              onClick={() => handleCancel(job.id)}
                              disabled={isLoadingAction}
                            >
                              {isLoadingAction ? (
                                <Loader2 className="size-4 animate-spin" />
                              ) : (
                                <Ban className="size-4" />
                              )}
                            </Button>
                          )}
                          {isRetryable && (
                            <Button
                              variant="ghost"
                              size="icon"
                              title="Retry import"
                              onClick={() => handleRetry(job.id)}
                              disabled={isLoadingAction}
                            >
                              {isLoadingAction ? (
                                <Loader2 className="size-4 animate-spin" />
                              ) : (
                                <RotateCcw className="size-4" />
                              )}
                            </Button>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </FadeIn>
        )}

        {/* ── Pagination ── */}
        {totalPages > 1 && (
          <FadeIn delay={0.3}>
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Showing {page * PAGE_SIZE + 1}–
                {Math.min((page + 1) * PAGE_SIZE, total)} of {total} imports
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0}
                >
                  <ChevronLeft className="size-4" />
                  Previous
                </Button>
                <span className="text-sm text-muted-foreground px-2">
                  Page {page + 1} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                  disabled={page >= totalPages - 1}
                >
                  Next
                  <ChevronRight className="size-4" />
                </Button>
              </div>
            </div>
          </FadeIn>
        )}

        {/* ── New Import Dialog ── */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="font-heading">New Import</DialogTitle>
              <DialogDescription>
                Paste a product URL from a supplier to import it into your store.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2">
              {/* Source Selector */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Source</label>
                <select
                  value={form.source}
                  onChange={(e) => handleFormChange("source", e.target.value)}
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
                  value={form.source_url}
                  onChange={(e) => handleFormChange("source_url", e.target.value)}
                />
              </div>

              {/* Store ID */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Store</label>
                <Input
                  placeholder="Store ID or name"
                  value={form.store_id}
                  onChange={(e) => handleFormChange("store_id", e.target.value)}
                />
              </div>

              {/* Markup Percent */}
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  Markup % ({form.markup_percent}%)
                </label>
                <Input
                  type="range"
                  min={0}
                  max={200}
                  step={5}
                  value={form.markup_percent}
                  onChange={(e) =>
                    handleFormChange("markup_percent", Number(e.target.value))
                  }
                  className="h-2 cursor-pointer"
                />
              </div>

              {/* Tags */}
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  Tags{" "}
                  <span className="text-muted-foreground font-normal">
                    (comma-separated)
                  </span>
                </label>
                <Input
                  placeholder="electronics, trending, summer"
                  value={form.tags}
                  onChange={(e) => handleFormChange("tags", e.target.value)}
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
                onClick={handleSubmit}
                disabled={
                  submitting || !form.source_url.trim() || !form.store_id.trim()
                }
              >
                {submitting ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Download className="size-4" />
                )}
                {submitting ? "Creating..." : "Start Import"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageTransition>
    </Shell>
  );
}
