/**
 * ResourceServiceStatus -- shows which connected services were notified
 * about a specific resource (product, order, or customer) and the
 * delivery outcome for each.
 *
 * **For Developers:**
 *   - Fetches data from
 *     `GET /api/v1/bridge/activity/{resource_type}/{resource_id}`.
 *   - Groups deliveries by service name and renders a compact grid.
 *   - Each service cell shows a status icon (check/x/dash), latency,
 *     and a relative timestamp.
 *   - Automatically handles loading, empty, and error states.
 *
 * **For QA Engineers:**
 *   - A green check icon indicates successful delivery.
 *   - A red X icon indicates a failed delivery.
 *   - A gray dash indicates the service was not triggered for this resource.
 *   - Latency is shown in milliseconds when available.
 *   - The component should gracefully handle API errors with a subtle message.
 *   - Loading state shows a skeleton grid.
 *
 * **For Project Managers:**
 *   This component gives store owners at-a-glance visibility into whether
 *   their connected AI services received a particular product or order event.
 *   It surfaces delivery failures early so users can take corrective action.
 *
 * **For End Users:**
 *   See which AI services were notified when you create or update a product
 *   or order. Green checks mean the service received the data; red marks
 *   indicate an issue that may need attention.
 */

"use client";

import { useEffect, useState } from "react";
import { Check, X, Minus } from "lucide-react";
import { api } from "@/lib/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  type BridgeDelivery,
  formatRelativeTime,
  formatServiceName,
} from "@/components/service-activity-card";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

/**
 * Props for the ResourceServiceStatus component.
 */
interface ResourceServiceStatusProps {
  /** The UUID of the resource (product, order, customer). */
  resourceId: string;
  /** The type of resource. */
  resourceType: "product" | "order" | "customer";
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** All known services in the platform. */
const ALL_SERVICES = [
  "trendscout",
  "contentforge",
  "pricepilot",
  "mailmaven",
  "adscale",
  "socialiq",
  "retarget",
  "reviewhub",
];

/**
 * Brand colors for each service, used for the icon background.
 *
 * @param name - Service slug.
 * @returns A hex color string.
 */
function getServiceColor(name: string): string {
  const colors: Record<string, string> = {
    trendscout: "#2563eb",
    contentforge: "#7c3aed",
    pricepilot: "#059669",
    mailmaven: "#d97706",
    adscale: "#dc2626",
    socialiq: "#0891b2",
    retarget: "#7c3aed",
    reviewhub: "#ea580c",
  };
  return colors[name] ?? "#6b7280";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Renders a compact grid showing delivery status per service for a resource.
 *
 * @param resourceId - The resource UUID.
 * @param resourceType - "product", "order", or "customer".
 * @returns A Card with a service status grid.
 */
export function ResourceServiceStatus({
  resourceId,
  resourceType,
}: ResourceServiceStatusProps) {
  const [deliveries, setDeliveries] = useState<BridgeDelivery[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    /**
     * Fetch bridge deliveries for this specific resource.
     */
    async function fetchDeliveries() {
      setLoading(true);
      setError(null);

      const result = await api.get<BridgeDelivery[]>(
        `/api/v1/bridge/activity/${resourceType}/${resourceId}`
      );

      if (result.error) {
        setError(result.error.message);
        setLoading(false);
        return;
      }

      setDeliveries(result.data ?? []);
      setLoading(false);
    }

    if (resourceId) {
      fetchDeliveries();
    }
  }, [resourceId, resourceType]);

  // Group deliveries by service, keeping only the most recent per service.
  const deliveryByService: Record<string, BridgeDelivery> = {};
  for (const d of deliveries) {
    const existing = deliveryByService[d.service_name];
    if (
      !existing ||
      new Date(d.created_at).getTime() > new Date(existing.created_at).getTime()
    ) {
      deliveryByService[d.service_name] = d;
    }
  }

  // Only show services that have deliveries (don't show ALL_SERVICES if none triggered).
  const triggeredServices = ALL_SERVICES.filter(
    (name) => deliveryByService[name]
  );
  const hasActivity = triggeredServices.length > 0 || deliveries.length > 0;

  // Loading state
  if (loading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-heading">
            Service Notifications
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-16 rounded-lg" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Error state
  if (error) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-heading">
            Service Notifications
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            Unable to load service status.
          </p>
        </CardContent>
      </Card>
    );
  }

  // Empty state -- no services were notified
  if (!hasActivity) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-heading">
            Service Notifications
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            No services have been notified about this {resourceType} yet.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-heading">
          Service Notifications
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {ALL_SERVICES.map((name) => {
            const delivery = deliveryByService[name];
            const color = getServiceColor(name);

            return (
              <div
                key={name}
                className="flex flex-col items-center gap-1.5 rounded-lg border p-3 bg-muted/20 hover:bg-muted/40 transition-colors"
              >
                {/* Status icon */}
                {delivery ? (
                  delivery.success ? (
                    <div className="flex size-7 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-900/30">
                      <Check className="size-3.5 text-emerald-600 dark:text-emerald-400" />
                    </div>
                  ) : (
                    <div className="flex size-7 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30">
                      <X className="size-3.5 text-red-600 dark:text-red-400" />
                    </div>
                  )
                ) : (
                  <div className="flex size-7 items-center justify-center rounded-full bg-muted">
                    <Minus className="size-3.5 text-muted-foreground/50" />
                  </div>
                )}

                {/* Service name */}
                <span
                  className="text-[11px] font-medium leading-tight text-center"
                  style={{ color: delivery ? color : undefined }}
                >
                  {formatServiceName(name)}
                </span>

                {/* Latency + timestamp */}
                {delivery && (
                  <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                    {delivery.latency_ms != null && (
                      <span className="font-mono">
                        {delivery.latency_ms}ms
                      </span>
                    )}
                    <span>{formatRelativeTime(delivery.created_at)}</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
