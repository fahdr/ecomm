/**
 * Service Activity page -- full activity log for all ServiceBridge
 * deliveries with filtering, summary stats, and pagination.
 *
 * **For Developers:**
 *   - Fetches from `GET /api/v1/bridge/activity` with query params for
 *     page, per_page, event, service, and status filtering.
 *   - Summary stats (total events, success rate, avg latency) are
 *     computed from `GET /api/v1/bridge/summary`.
 *   - Each delivery row shows status dot, service icon + name, event
 *     badge, resource type + truncated ID, latency, and timestamp.
 *   - Pagination controls at the bottom allow navigating between pages.
 *   - Uses DashboardShell wrapper and PageTransition animation.
 *
 * **For QA Engineers:**
 *   - Page should load with skeleton placeholders while fetching.
 *   - Summary bar should show total events, success rate percentage,
 *     average latency in milliseconds, and failure count.
 *   - Filter dropdowns for event type, service name, and status should
 *     trigger a re-fetch when changed.
 *   - Pagination buttons should be disabled at bounds (first/last page).
 *   - Each row should link the resource ID back to the product or order
 *     detail page.
 *   - Empty state should show when no deliveries match the filters.
 *
 * **For Project Managers:**
 *   The Service Activity page provides operations-level visibility into
 *   every event dispatched through the ServiceBridge. It helps identify
 *   failing integrations, slow services, and delivery issues.
 *
 * **For End Users:**
 *   Monitor every event sent from your store to your connected AI
 *   services. Use the filters to find specific events and diagnose any
 *   integration issues.
 */

"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  ChevronLeft,
  ChevronRight,
  Filter,
  ArrowLeft,
  CheckCircle2,
  XCircle,
  Clock,
  Zap,
} from "lucide-react";
import { useAuth } from "@/contexts/auth-context";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import { PageTransition, FadeIn } from "@/components/motion-wrappers";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  type BridgeDelivery,
  type BridgeActivityResponse,
  type ServiceSummary,
  formatRelativeTime,
  formatServiceName,
} from "@/components/service-activity-card";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Known event types for the filter dropdown. */
const EVENT_TYPES = [
  "product.created",
  "product.updated",
  "product.deleted",
  "order.created",
  "order.paid",
  "order.shipped",
  "order.delivered",
  "order.cancelled",
  "customer.created",
  "customer.updated",
];

/** All known services for the filter dropdown. */
const SERVICE_NAMES = [
  "trendscout",
  "contentforge",
  "pricepilot",
  "mailmaven",
  "adscale",
  "socialiq",
  "retarget",
  "reviewhub",
];

const PER_PAGE = 20;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Maps event type prefixes to Tailwind badge color classes.
 *
 * @param event - The event string (e.g. "product.created").
 * @returns Tailwind classes for the badge background and text.
 */
function getEventBadgeClasses(event: string): string {
  if (event.startsWith("product.created")) return "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400";
  if (event.startsWith("product.updated")) return "bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-400";
  if (event.startsWith("product.")) return "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400";
  if (event.startsWith("order.created")) return "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400";
  if (event.startsWith("order.shipped")) return "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400";
  if (event.startsWith("order.")) return "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400";
  if (event.startsWith("customer.")) return "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400";
  return "bg-muted text-muted-foreground";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Full-page activity log with filtering and pagination.
 *
 * @returns The service activity page wrapped in PageTransition.
 */
export default function ServiceActivityPage() {
  const { user, loading: authLoading } = useAuth();
  const { store } = useStore();
  const storeId = store?.id;

  // Data state
  const [activityData, setActivityData] = useState<BridgeActivityResponse | null>(null);
  const [summaryData, setSummaryData] = useState<ServiceSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [eventFilter, setEventFilter] = useState<string>("all");
  const [serviceFilter, setServiceFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [page, setPage] = useState(1);

  /**
   * Build the query string from the current filter and pagination state.
   *
   * @returns The URL query parameter string.
   */
  function buildQueryParams(): string {
    const params = new URLSearchParams();
    params.set("page", String(page));
    params.set("per_page", String(PER_PAGE));
    if (eventFilter !== "all") params.set("event", eventFilter);
    if (serviceFilter !== "all") params.set("service", serviceFilter);
    if (statusFilter !== "all") params.set("status", statusFilter);
    return params.toString();
  }

  /**
   * Fetch activity data and summary from the bridge API.
   * Called on mount and whenever filters or page change.
   */
  const fetchData = useCallback(async () => {
    setError(null);
    const queryStr = buildQueryParams();

    const [activityRes, summaryRes] = await Promise.all([
      api.get<BridgeActivityResponse>(`/api/v1/bridge/activity?${queryStr}`),
      api.get<ServiceSummary[]>("/api/v1/bridge/summary"),
    ]);

    if (activityRes.error) {
      setError(activityRes.error.message);
      setLoading(false);
      return;
    }

    setActivityData(activityRes.data);
    if (summaryRes.data) setSummaryData(summaryRes.data);
    setLoading(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, eventFilter, serviceFilter, statusFilter]);

  useEffect(() => {
    if (authLoading || !user) return;
    setLoading(true);
    fetchData();
  }, [user, authLoading, fetchData]);

  /**
   * Reset page to 1 when a filter changes.
   *
   * @param setter - The state setter for the filter.
   * @param value - The new filter value.
   */
  function handleFilterChange(
    setter: (v: string) => void,
    value: string
  ) {
    setter(value);
    setPage(1);
  }

  // Derived summary stats
  const totalEvents = summaryData.reduce(
    (sum, s) => sum + (s.failure_count_24h >= 0 ? 1 : 0),
    activityData?.total ?? 0
  );
  const totalFailures24h = summaryData.reduce(
    (sum, s) => sum + s.failure_count_24h,
    0
  );
  const successRate =
    totalEvents > 0
      ? Math.round(((totalEvents - totalFailures24h) / totalEvents) * 100)
      : 100;

  // Average latency from the current page of deliveries
  const deliveries = activityData?.items ?? [];
  const latencies = deliveries
    .filter((d) => d.latency_ms != null)
    .map((d) => d.latency_ms!);
  const avgLatency =
    latencies.length > 0
      ? Math.round(latencies.reduce((a, b) => a + b, 0) / latencies.length)
      : 0;

  const totalPages = activityData?.pages ?? 1;

  // Loading skeleton
  if (loading) {
    return (
      <div className="mx-auto max-w-6xl p-6 space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-12 w-full rounded-xl" />
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-12 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <PageTransition>
      <main className="mx-auto max-w-6xl p-6 space-y-6">
        {/* Back navigation */}
        <FadeIn>
          <Link
            href={`/stores/${storeId}/services`}
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="size-4" />
            Back to Services
          </Link>
        </FadeIn>

        {/* Page header */}
        <FadeIn delay={0.05}>
          <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-2xl font-heading font-bold flex items-center gap-2">
                <Activity className="size-6 text-primary" />
                Service Activity
              </h1>
              <p className="text-sm text-muted-foreground mt-1">
                Monitor events dispatched to your connected services
              </p>
            </div>
            {activityData && (
              <Badge variant="outline" className="w-fit text-xs font-mono">
                {activityData.total.toLocaleString()} total events
              </Badge>
            )}
          </div>
        </FadeIn>

        {/* Summary Stats */}
        <FadeIn delay={0.1}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-5 pb-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Total Events
                    </p>
                    <p className="text-2xl font-bold mt-1 font-mono">
                      {(activityData?.total ?? 0).toLocaleString()}
                    </p>
                  </div>
                  <div className="p-2 rounded-lg bg-muted/50 text-primary">
                    <Zap className="size-5" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-5 pb-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Success Rate
                    </p>
                    <p className="text-2xl font-bold mt-1 font-mono">
                      {successRate}%
                    </p>
                  </div>
                  <div className="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 className="size-5" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-5 pb-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Avg Latency
                    </p>
                    <p className="text-2xl font-bold mt-1 font-mono">
                      {avgLatency}ms
                    </p>
                  </div>
                  <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400">
                    <Clock className="size-5" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-5 pb-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Failures (24h)
                    </p>
                    <p className="text-2xl font-bold mt-1 font-mono">
                      {totalFailures24h}
                    </p>
                  </div>
                  <div className="p-2 rounded-lg bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400">
                    <XCircle className="size-5" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </FadeIn>

        {/* Filters */}
        <FadeIn delay={0.15}>
          <Card variant="glass">
            <CardContent className="pt-5 pb-4">
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
                <div className="flex items-center gap-1.5 text-sm text-muted-foreground shrink-0">
                  <Filter className="size-4" />
                  Filters
                </div>

                <Select
                  value={eventFilter}
                  onValueChange={(v) => handleFilterChange(setEventFilter, v)}
                >
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Event type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Events</SelectItem>
                    {EVENT_TYPES.map((e) => (
                      <SelectItem key={e} value={e}>
                        {e}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select
                  value={serviceFilter}
                  onValueChange={(v) => handleFilterChange(setServiceFilter, v)}
                >
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Service" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Services</SelectItem>
                    {SERVICE_NAMES.map((s) => (
                      <SelectItem key={s} value={s}>
                        {formatServiceName(s)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select
                  value={statusFilter}
                  onValueChange={(v) => handleFilterChange(setStatusFilter, v)}
                >
                  <SelectTrigger className="w-[140px]">
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Statuses</SelectItem>
                    <SelectItem value="success">Success</SelectItem>
                    <SelectItem value="failure">Failure</SelectItem>
                  </SelectContent>
                </Select>

                {(eventFilter !== "all" ||
                  serviceFilter !== "all" ||
                  statusFilter !== "all") && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-xs"
                    onClick={() => {
                      setEventFilter("all");
                      setServiceFilter("all");
                      setStatusFilter("all");
                      setPage(1);
                    }}
                  >
                    Clear Filters
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        </FadeIn>

        {/* Error state */}
        {error && (
          <FadeIn>
            <Card className="border-destructive/50">
              <CardContent className="pt-5 pb-4">
                <p className="text-sm text-destructive">{error}</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2"
                  onClick={() => {
                    setError(null);
                    setLoading(true);
                    fetchData();
                  }}
                >
                  Retry
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        )}

        {/* Activity list */}
        <FadeIn delay={0.2}>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-heading">
                Delivery Log
              </CardTitle>
            </CardHeader>
            <CardContent>
              {deliveries.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-10 text-center">
                  <Activity className="size-8 text-muted-foreground/30 mb-3" />
                  <p className="text-sm text-muted-foreground">
                    No deliveries match the current filters.
                  </p>
                  <p className="text-xs text-muted-foreground/70 mt-1">
                    Try adjusting the filters above or wait for new events.
                  </p>
                </div>
              ) : (
                <div className="space-y-1">
                  {deliveries.map((d) => (
                    <ActivityRow key={d.id} delivery={d} storeId={storeId ?? ""} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </FadeIn>

        {/* Pagination */}
        {activityData && activityData.pages > 1 && (
          <FadeIn delay={0.25}>
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Page {page} of {totalPages} ({activityData.total.toLocaleString()} total)
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="gap-1"
                >
                  <ChevronLeft className="size-4" />
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                  className="gap-1"
                >
                  Next
                  <ChevronRight className="size-4" />
                </Button>
              </div>
            </div>
          </FadeIn>
        )}
      </main>
    </PageTransition>
  );
}

// ---------------------------------------------------------------------------
// Sub-component: ActivityRow
// ---------------------------------------------------------------------------

/**
 * A single row in the delivery log table.
 *
 * @param delivery - The delivery record to render.
 * @param storeId - The current store ID for resource links.
 * @returns A div representing one delivery event.
 */
function ActivityRow({
  delivery: d,
  storeId,
}: {
  delivery: BridgeDelivery;
  storeId: string;
}) {
  /**
   * Build a link to the resource detail page based on resource type.
   *
   * @returns A relative URL path, or null if the type is unknown.
   */
  function getResourceLink(): string | null {
    if (d.resource_type === "product") {
      return `/stores/${storeId}/products/${d.resource_id}`;
    }
    if (d.resource_type === "order") {
      return `/stores/${storeId}/orders/${d.resource_id}`;
    }
    return null;
  }

  const resourceLink = getResourceLink();
  const resourceLabel = `${d.resource_type}/${d.resource_id.slice(0, 8)}...`;

  return (
    <div>
      <div className="flex items-center gap-3 py-2.5 px-3 rounded-md hover:bg-muted/30 transition-colors">
        {/* Status dot */}
        <div
          className={`size-2.5 rounded-full shrink-0 ${
            d.success ? "bg-emerald-500" : "bg-red-500"
          }`}
          title={d.success ? "Success" : "Failed"}
        />

        {/* Service name */}
        <span className="text-xs font-medium w-24 shrink-0 truncate">
          {formatServiceName(d.service_name)}
        </span>

        {/* Event badge */}
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium leading-tight shrink-0 ${getEventBadgeClasses(
            d.event
          )}`}
        >
          {d.event}
        </span>

        {/* Resource link */}
        {resourceLink ? (
          <Link
            href={resourceLink}
            className="text-xs text-muted-foreground hover:text-foreground font-mono truncate transition-colors"
          >
            {resourceLabel}
          </Link>
        ) : (
          <span className="text-xs text-muted-foreground font-mono truncate">
            {resourceLabel}
          </span>
        )}

        {/* HTTP status */}
        {d.response_status != null && (
          <Badge
            variant={
              d.response_status >= 200 && d.response_status < 300
                ? "outline"
                : "destructive"
            }
            className="text-[10px] px-1.5 py-0 shrink-0"
          >
            {d.response_status}
          </Badge>
        )}

        <div className="flex items-center gap-3 ml-auto shrink-0">
          {/* Latency */}
          {d.latency_ms != null && (
            <span className="text-[10px] text-muted-foreground font-mono">
              {d.latency_ms}ms
            </span>
          )}

          {/* Timestamp */}
          <span className="text-[10px] text-muted-foreground tabular-nums w-14 text-right">
            {formatRelativeTime(d.created_at)}
          </span>
        </div>
      </div>

      {/* Error message for failures */}
      {!d.success && d.error_message && (
        <p className="text-[11px] text-destructive/80 pl-8 pb-1 leading-snug">
          {d.error_message}
        </p>
      )}
    </div>
  );
}
