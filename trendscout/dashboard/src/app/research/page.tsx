/**
 * Research page — main hub for product research runs.
 *
 * Displays the user's research run history in a sortable list, with status
 * indicators and result counts. Provides a dialog to start new research
 * runs by entering keywords and selecting data sources.
 *
 * **For Developers:**
 *   - Fetches from `GET /api/v1/research/runs` on mount with pagination.
 *   - Creates new runs via `POST /api/v1/research/runs`.
 *   - Deletes runs via `DELETE /api/v1/research/runs/{id}`.
 *   - Uses the Dialog component for the "New Research" modal form.
 *   - Status badges use color-coded variants: pending (secondary),
 *     running (default/primary), completed (success), failed (destructive).
 *   - Stagger and FadeIn animations provide polished entrance effects.
 *
 * **For Project Managers:**
 *   - This is the primary feature page — where users start product research.
 *   - Research runs are the main metered resource (limited by plan tier).
 *   - The "New Research" dialog captures keywords and source selections.
 *
 * **For QA Engineers:**
 *   - Verify loading skeletons appear while data is being fetched.
 *   - Test creating a run: dialog opens, form validates, run appears in list.
 *   - Test deleting a run: confirm prompt, item removed from list.
 *   - Test pagination: navigate between pages of results.
 *   - Test with API server down — error state, not crash.
 *   - Check status badge colors match run status values.
 *
 * **For End Users:**
 *   - Start a new product research run by clicking "New Research".
 *   - Enter keywords describing what products you want to find.
 *   - Select which data sources to scan (AliExpress, TikTok, etc.).
 *   - View your run history and click a run to see its results.
 *   - Delete old runs to keep your history clean.
 */

"use client";

import * as React from "react";
import {
  Search,
  Plus,
  Trash2,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  FlaskConical,
  ChevronLeft,
  ChevronRight,
  ArrowUpRight,
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

/** Shape of a research run from the backend API. */
interface ResearchRun {
  id: string;
  user_id: string;
  keywords: string[];
  sources: string[];
  status: string;
  score_config: Record<string, number> | null;
  results_count: number;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  results: unknown[];
}

/** Paginated list response from GET /api/v1/research/runs. */
interface ResearchRunListResponse {
  items: ResearchRun[];
  total: number;
  page: number;
  per_page: number;
}

/** Available data sources for research runs. */
const AVAILABLE_SOURCES = [
  { id: "aliexpress", label: "AliExpress", description: "Product listings & pricing" },
  { id: "google_trends", label: "Google Trends", description: "Search interest data" },
  { id: "tiktok", label: "TikTok", description: "Viral product discovery" },
  { id: "reddit", label: "Reddit", description: "Community discussions & reviews" },
] as const;

/* ── Helper Functions ──────────────────────────────────────────────── */

/**
 * Map a run status string to a Badge variant and icon.
 *
 * @param status - The run status (pending, running, completed, failed).
 * @returns Object with variant string and Icon component.
 */
function getStatusConfig(status: string): {
  variant: "secondary" | "default" | "success" | "destructive";
  Icon: React.ComponentType<{ className?: string }>;
  label: string;
} {
  switch (status) {
    case "running":
      return { variant: "default", Icon: Loader2, label: "Running" };
    case "completed":
      return { variant: "success", Icon: CheckCircle2, label: "Completed" };
    case "failed":
      return { variant: "destructive", Icon: XCircle, label: "Failed" };
    case "pending":
    default:
      return { variant: "secondary", Icon: Clock, label: "Pending" };
  }
}

/**
 * Format a date string to a human-readable relative/absolute format.
 *
 * @param dateStr - ISO 8601 date string from the API.
 * @returns Formatted date string (e.g. "Jan 15, 2024 at 3:42 PM").
 */
function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/* ── Main Page Component ───────────────────────────────────────────── */

/**
 * Research page component — lists runs, creates new runs, manages history.
 *
 * @returns The research page wrapped in the Shell layout.
 */
export default function ResearchPage() {
  /* ── State ── */
  const [runs, setRuns] = React.useState<ResearchRun[]>([]);
  const [total, setTotal] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [perPage] = React.useState(10);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  /* New run dialog state */
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [keywordInput, setKeywordInput] = React.useState("");
  const [selectedSources, setSelectedSources] = React.useState<string[]>([
    "aliexpress",
    "google_trends",
  ]);
  const [creating, setCreating] = React.useState(false);
  const [createError, setCreateError] = React.useState<string | null>(null);

  /* Delete confirmation */
  const [deletingId, setDeletingId] = React.useState<string | null>(null);

  /* ── Data Fetching ── */

  /**
   * Fetch research runs from the backend with current pagination.
   * Updates the runs list, total count, and loading/error state.
   */
  const fetchRuns = React.useCallback(async () => {
    setLoading(true);
    setError(null);

    const { data, error: apiError } =
      await api.get<ResearchRunListResponse>(
        `/api/v1/research/runs?page=${page}&per_page=${perPage}`
      );

    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setRuns(data.items);
      setTotal(data.total);
    }
    setLoading(false);
  }, [page, perPage]);

  React.useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  /* ── Handlers ── */

  /**
   * Toggle a source in the selected sources array.
   *
   * @param sourceId - The source identifier to toggle.
   */
  function toggleSource(sourceId: string) {
    setSelectedSources((prev) =>
      prev.includes(sourceId)
        ? prev.filter((s) => s !== sourceId)
        : [...prev, sourceId]
    );
  }

  /**
   * Create a new research run from the dialog form data.
   * Parses comma-separated keywords, validates input, and calls the API.
   */
  async function handleCreateRun() {
    setCreateError(null);

    /* Parse keywords from comma-separated input */
    const keywords = keywordInput
      .split(",")
      .map((k) => k.trim())
      .filter((k) => k.length > 0);

    if (keywords.length === 0) {
      setCreateError("Enter at least one keyword.");
      return;
    }

    if (selectedSources.length === 0) {
      setCreateError("Select at least one data source.");
      return;
    }

    setCreating(true);

    const { error: apiError } = await api.post<ResearchRun>(
      "/api/v1/research/runs",
      { keywords, sources: selectedSources }
    );

    if (apiError) {
      setCreateError(apiError.message);
      setCreating(false);
      return;
    }

    /* Reset form and refresh list */
    setKeywordInput("");
    setSelectedSources(["aliexpress", "google_trends"]);
    setCreating(false);
    setDialogOpen(false);
    setPage(1);
    fetchRuns();
  }

  /**
   * Delete a research run by ID and refresh the list.
   *
   * @param runId - The UUID of the run to delete.
   */
  async function handleDeleteRun(runId: string) {
    setDeletingId(runId);

    const { error: apiError } = await api.del(`/api/v1/research/runs/${runId}`);

    if (!apiError) {
      fetchRuns();
    }
    setDeletingId(null);
  }

  /* ── Derived Values ── */
  const totalPages = Math.ceil(total / perPage);
  const completedCount = runs.filter((r) => r.status === "completed").length;
  const pendingCount = runs.filter(
    (r) => r.status === "pending" || r.status === "running"
  ).length;

  /* ── Render ── */
  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* ── Page Header ── */}
        <FadeIn direction="down">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight flex items-center gap-2">
                <Search className="size-6" />
                Product Research
              </h2>
              <p className="text-muted-foreground mt-1">
                Discover trending products across multiple data sources.
              </p>
            </div>
            <Button onClick={() => setDialogOpen(true)}>
              <Plus className="size-4" />
              New Research
            </Button>
          </div>
        </FadeIn>

        {/* ── Summary KPI Cards ── */}
        <StaggerChildren
          className="grid grid-cols-1 md:grid-cols-3 gap-4"
          staggerDelay={0.08}
        >
          {/* Total Runs */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Runs
              </CardTitle>
              <FlaskConical className="size-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {loading ? (
                <Skeleton className="h-8 w-16" />
              ) : (
                <AnimatedCounter
                  value={total}
                  className="text-3xl font-bold font-heading"
                />
              )}
            </CardContent>
          </Card>

          {/* Completed */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Completed
              </CardTitle>
              <CheckCircle2 className="size-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              {loading ? (
                <Skeleton className="h-8 w-16" />
              ) : (
                <AnimatedCounter
                  value={completedCount}
                  className="text-3xl font-bold font-heading text-emerald-600"
                />
              )}
            </CardContent>
          </Card>

          {/* In Progress */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                In Progress
              </CardTitle>
              <Loader2 className="size-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {loading ? (
                <Skeleton className="h-8 w-16" />
              ) : (
                <AnimatedCounter
                  value={pendingCount}
                  className="text-3xl font-bold font-heading"
                />
              )}
            </CardContent>
          </Card>
        </StaggerChildren>

        {/* ── Runs List ── */}
        <FadeIn delay={0.2}>
          <Card>
            <CardHeader>
              <CardTitle>Research History</CardTitle>
              <CardDescription>
                Your recent product research runs and their results.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                /* Loading skeleton for the runs list */
                <div className="space-y-4">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between p-4 border rounded-lg"
                    >
                      <div className="space-y-2 flex-1">
                        <Skeleton className="h-4 w-48" />
                        <Skeleton className="h-3 w-32" />
                      </div>
                      <Skeleton className="h-6 w-20" />
                    </div>
                  ))}
                </div>
              ) : error ? (
                /* Error state */
                <div className="text-center py-12">
                  <XCircle className="size-10 text-destructive mx-auto mb-3" />
                  <p className="text-destructive text-sm">{error}</p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-4"
                    onClick={() => fetchRuns()}
                  >
                    Retry
                  </Button>
                </div>
              ) : runs.length === 0 ? (
                /* Empty state */
                <div className="text-center py-16">
                  <div className="size-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
                    <Search className="size-7 text-primary" />
                  </div>
                  <h3 className="font-heading font-semibold text-lg">
                    No research runs yet
                  </h3>
                  <p className="text-muted-foreground text-sm mt-1 max-w-sm mx-auto">
                    Start your first product research run to discover trending
                    products across multiple data sources.
                  </p>
                  <Button className="mt-5" onClick={() => setDialogOpen(true)}>
                    <Plus className="size-4" />
                    Start Research
                  </Button>
                </div>
              ) : (
                /* Runs list */
                <div className="space-y-3">
                  {runs.map((run) => {
                    const { variant, Icon, label } = getStatusConfig(
                      run.status
                    );
                    return (
                      <div
                        key={run.id}
                        className="flex items-center justify-between p-4 border rounded-lg hover:bg-secondary/30 transition-colors group"
                      >
                        {/* Run Info */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <p className="font-medium text-sm truncate">
                              {run.keywords.join(", ")}
                            </p>
                            <Badge variant={variant} className="shrink-0">
                              <Icon
                                className={`size-3 mr-1 ${
                                  run.status === "running"
                                    ? "animate-spin"
                                    : ""
                                }`}
                              />
                              {label}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-4 text-xs text-muted-foreground">
                            <span>{formatDate(run.created_at)}</span>
                            <span className="flex items-center gap-1">
                              <FlaskConical className="size-3" />
                              {run.results_count} result
                              {run.results_count !== 1 ? "s" : ""}
                            </span>
                            <span>
                              Sources:{" "}
                              {run.sources
                                .map((s) =>
                                  s.replace("_", " ").replace(/\b\w/g, (c) =>
                                    c.toUpperCase()
                                  )
                                )
                                .join(", ")}
                            </span>
                          </div>
                          {run.error_message && (
                            <p className="text-xs text-destructive mt-1">
                              {run.error_message}
                            </p>
                          )}
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-2 ml-4 opacity-0 group-hover:opacity-100 transition-opacity">
                          {run.results_count > 0 && (
                            <Button variant="ghost" size="sm" asChild>
                              <a href={`/research/${run.id}`}>
                                <ArrowUpRight className="size-3.5" />
                                View
                              </a>
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-muted-foreground hover:text-destructive"
                            onClick={() => handleDeleteRun(run.id)}
                            disabled={deletingId === run.id}
                          >
                            {deletingId === run.id ? (
                              <Loader2 className="size-4 animate-spin" />
                            ) : (
                              <Trash2 className="size-4" />
                            )}
                          </Button>
                        </div>
                      </div>
                    );
                  })}

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-between pt-4 border-t">
                      <p className="text-sm text-muted-foreground">
                        Showing {(page - 1) * perPage + 1}
                        {" "}-{" "}
                        {Math.min(page * perPage, total)} of {total} runs
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
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </FadeIn>

        {/* ── New Research Dialog ── */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Search className="size-5" />
                New Product Research
              </DialogTitle>
              <DialogDescription>
                Enter keywords and select data sources to scan for trending products.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-5 py-2">
              {/* Keywords input */}
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  Keywords
                  <span className="text-muted-foreground font-normal ml-1">
                    (comma-separated)
                  </span>
                </label>
                <Input
                  placeholder="wireless earbuds, phone case, yoga mat"
                  value={keywordInput}
                  onChange={(e) => setKeywordInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleCreateRun();
                    }
                  }}
                />
                <p className="text-xs text-muted-foreground">
                  Enter up to 10 keywords to research across selected sources.
                </p>
              </div>

              {/* Source selection */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Data Sources</label>
                <div className="grid grid-cols-2 gap-2">
                  {AVAILABLE_SOURCES.map((source) => {
                    const isSelected = selectedSources.includes(source.id);
                    return (
                      <button
                        key={source.id}
                        type="button"
                        onClick={() => toggleSource(source.id)}
                        className={`p-3 rounded-lg border text-left transition-all duration-150 ${
                          isSelected
                            ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                            : "border-input hover:bg-secondary/50"
                        }`}
                      >
                        <p className="text-sm font-medium">{source.label}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {source.description}
                        </p>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Error message */}
              {createError && (
                <p className="text-sm text-destructive">{createError}</p>
              )}
            </div>

            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline">Cancel</Button>
              </DialogClose>
              <Button onClick={handleCreateRun} disabled={creating}>
                {creating ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    Starting...
                  </>
                ) : (
                  <>
                    <FlaskConical className="size-4" />
                    Start Research
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageTransition>
    </Shell>
  );
}
