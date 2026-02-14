/**
 * ServiceActivityCard -- reusable card displaying a list of ServiceBridge
 * delivery records with status indicators, service names, event badges,
 * and relative timestamps.
 *
 * **For Developers:**
 *   - Accepts an array of `BridgeDelivery` objects and renders them as
 *     a compact list inside a Card.
 *   - `showServiceName` controls whether the service column appears
 *     (useful when the card is already scoped to a single service).
 *   - `maxItems` truncates the list; combine with `viewAllHref` to let
 *     users navigate to the full activity log.
 *   - `isLoading` renders skeleton rows instead of delivery data.
 *   - Uses `formatRelativeTime` for human-friendly timestamps.
 *
 * **For QA Engineers:**
 *   - Successful deliveries show a green status dot; failures show red.
 *   - Failed deliveries display the error message in muted text below
 *     the main row.
 *   - The "View All" link should only appear when `viewAllHref` is set.
 *   - Loading state should show 3 skeleton rows by default.
 *   - Empty state shows a subtle "No activity yet" message.
 *   - Event badges use color-coded backgrounds (see EVENT_BADGE_COLORS).
 *
 * **For Project Managers:**
 *   This component is the primary building block for exposing
 *   ServiceBridge delivery data throughout the dashboard. It appears on
 *   the store overview, service detail, and dedicated activity pages.
 *
 * **For End Users:**
 *   See a live feed of events sent to your connected AI services.
 *   Green dots mean the service received the event successfully; red
 *   dots indicate a delivery failure.
 */

"use client";

import Link from "next/link";
import { ArrowRight, AlertCircle } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * A single ServiceBridge delivery record.
 *
 * Represents one event dispatched to a connected service, including
 * whether it succeeded, latency, and any error details.
 */
export interface BridgeDelivery {
  /** Unique delivery ID. */
  id: string;
  /** The target service name (e.g. "trendscout"). */
  service_name: string;
  /** The event type (e.g. "product.created", "order.shipped"). */
  event: string;
  /** The originating resource ID (product, order, etc.). */
  resource_id: string;
  /** The resource type ("product", "order", "customer"). */
  resource_type: string;
  /** Whether the delivery succeeded. */
  success: boolean;
  /** Error message if delivery failed. */
  error_message: string | null;
  /** HTTP response status from the service. */
  response_status: number | null;
  /** Round-trip latency in milliseconds. */
  latency_ms: number | null;
  /** ISO 8601 timestamp of when the delivery occurred. */
  created_at: string;
}

/**
 * Paginated response envelope for bridge activity queries.
 */
export interface BridgeActivityResponse {
  items: BridgeDelivery[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

/**
 * Aggregate health summary for a single connected service.
 */
export interface ServiceSummary {
  service_name: string;
  last_event_at: string | null;
  last_success: boolean | null;
  failure_count_24h: number;
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

/**
 * Props for the ServiceActivityCard component.
 */
interface ServiceActivityCardProps {
  /** The list of delivery records to display. */
  deliveries: BridgeDelivery[];
  /** Card title. Defaults to "Recent Activity". */
  title?: string;
  /** Whether to show the service name column. Defaults to true. */
  showServiceName?: boolean;
  /** Maximum number of rows to render. Defaults to all. */
  maxItems?: number;
  /** URL for the "View All" link. Omit to hide the link. */
  viewAllHref?: string;
  /** When true, renders skeleton rows instead of data. */
  isLoading?: boolean;
}

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

/**
 * Convert an ISO date string to a human-friendly relative time.
 *
 * @param dateStr - ISO 8601 date string.
 * @returns Relative time string (e.g. "2m ago", "3h ago", "1d ago").
 */
export function formatRelativeTime(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

/**
 * Human-readable display name for a service slug.
 *
 * @param name - Service slug (e.g. "trendscout").
 * @returns Display-friendly name.
 */
export function formatServiceName(name: string): string {
  const map: Record<string, string> = {
    trendscout: "TrendScout",
    contentforge: "ContentForge",
    pricepilot: "PricePilot",
    mailmaven: "MailMaven",
    adscale: "AdScale",
    socialiq: "SocialIQ",
    retarget: "Retarget",
    reviewhub: "ReviewHub",
  };
  return map[name] ?? name.charAt(0).toUpperCase() + name.slice(1);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Renders a card with a list of ServiceBridge delivery records.
 *
 * @param deliveries - Array of delivery records.
 * @param title - Card heading text.
 * @param showServiceName - Whether to render the service name column.
 * @param maxItems - Maximum rows to display.
 * @param viewAllHref - Optional URL for a "View All" link.
 * @param isLoading - Render skeleton state when true.
 * @returns A Card element with delivery list, loading, or empty state.
 */
export function ServiceActivityCard({
  deliveries,
  title = "Recent Activity",
  showServiceName = true,
  maxItems,
  viewAllHref,
  isLoading = false,
}: ServiceActivityCardProps) {
  const visibleDeliveries = maxItems
    ? deliveries.slice(0, maxItems)
    : deliveries;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-heading">{title}</CardTitle>
          {viewAllHref && (
            <Link
              href={viewAllHref}
              className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              View All
              <ArrowRight className="size-3" />
            </Link>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {/* Loading state */}
        {isLoading && (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3">
                <Skeleton className="size-2 rounded-full shrink-0" />
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-5 w-24 rounded-full" />
                <Skeleton className="h-4 w-12 ml-auto" />
              </div>
            ))}
          </div>
        )}

        {/* Empty state */}
        {!isLoading && deliveries.length === 0 && (
          <div className="flex flex-col items-center justify-center py-6 text-center">
            <AlertCircle className="size-5 text-muted-foreground/50 mb-2" />
            <p className="text-sm text-muted-foreground">No activity yet</p>
            <p className="text-xs text-muted-foreground/70 mt-0.5">
              Events will appear here once services start receiving data.
            </p>
          </div>
        )}

        {/* Delivery list */}
        {!isLoading && visibleDeliveries.length > 0 && (
          <div className="space-y-1.5">
            {visibleDeliveries.map((d) => (
              <div key={d.id}>
                <div className="flex items-center gap-3 py-2 px-2 rounded-md hover:bg-muted/30 transition-colors">
                  {/* Status dot */}
                  <div
                    className={`size-2 rounded-full shrink-0 ${
                      d.success ? "bg-emerald-500" : "bg-red-500"
                    }`}
                    title={d.success ? "Success" : "Failed"}
                  />

                  {/* Service name */}
                  {showServiceName && (
                    <span className="text-xs font-medium truncate min-w-[72px] max-w-[100px]">
                      {formatServiceName(d.service_name)}
                    </span>
                  )}

                  {/* Event badge */}
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium leading-tight ${getEventBadgeClasses(
                      d.event
                    )}`}
                  >
                    {d.event}
                  </span>

                  {/* Latency */}
                  {d.latency_ms != null && (
                    <span className="text-[10px] text-muted-foreground font-mono ml-auto shrink-0">
                      {d.latency_ms}ms
                    </span>
                  )}

                  {/* Timestamp */}
                  <span className="text-[10px] text-muted-foreground shrink-0 tabular-nums">
                    {formatRelativeTime(d.created_at)}
                  </span>
                </div>

                {/* Error message for failures */}
                {!d.success && d.error_message && (
                  <p className="text-[11px] text-destructive/80 pl-7 pb-1 leading-snug">
                    {d.error_message}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
