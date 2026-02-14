/**
 * Services Hub page -- browse, enable, and manage all 8 AI & Automation services.
 *
 * Displays a card grid of available microservices with connection status,
 * usage meters for connected services, and enable/disable actions.
 *
 * **For Developers:**
 *   - Fetches from `GET /api/v1/services` (auth) which returns all 8 services
 *     annotated with the user's connection state.
 *   - Uses `GET /api/v1/services/usage/summary` for the header usage bar.
 *   - Provisioning calls `POST /api/v1/services/{name}/provision`.
 *   - The icon string from the backend (e.g. "search", "pencil") is mapped
 *     to Lucide React components via `SERVICE_ICON_MAP`.
 *   - Each service card links to `/stores/[id]/services/[service]` for details.
 *
 * **For QA Engineers:**
 *   - Page should load with a skeleton grid while fetching.
 *   - All 8 service cards must appear.
 *   - Connected services show a green status dot, current tier badge, and
 *     "Open Dashboard" + "Details" buttons.
 *   - Disconnected services show an "Enable" button that opens a confirmation
 *     dialog, then provisions on the free tier.
 *   - After enabling, the card should update to show connected state.
 *   - Header shows total connected count and monthly cost.
 *   - Error states (failed fetch, failed provision) show inline messages.
 *
 * **For Project Managers:**
 *   This is the main entry point for the AI & Automation feature in the
 *   dashboard. Users can see all available services at a glance and manage
 *   connections from one page.
 *
 * **For End Users:**
 *   Browse all AI-powered tools available for your dropshipping business.
 *   Enable services with one click to get started on the free tier, or
 *   click into a service for detailed usage and plan management.
 */

"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "motion/react";
import {
  Search,
  Pencil,
  TrendingUp,
  Mail,
  Eye,
  Share2,
  Target,
  MessageCircle,
  Zap,
  ExternalLink,
  ChevronRight,
  Sparkles,
  CircleDot,
} from "lucide-react";
import { useAuth } from "@/contexts/auth-context";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import { PageTransition, FadeIn, StaggerChildren, staggerItem } from "@/components/motion-wrappers";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  type ServiceSummary,
  formatRelativeTime,
} from "@/components/service-activity-card";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Tier pricing information for a service. */
interface ServiceTierInfo {
  tier: string;
  name: string;
  price_monthly_cents: number;
  features: string[];
}

/** Static catalog information for a service. */
interface ServiceInfo {
  name: string;
  display_name: string;
  tagline: string;
  description: string;
  icon: string;
  color: string;
  dashboard_url: string;
  landing_url: string;
  tiers: ServiceTierInfo[];
}

/** A service's connection status for the current user. */
interface ServiceStatus {
  service: ServiceInfo;
  is_connected: boolean;
  integration_id: string | null;
  current_tier: string | null;
  is_active: boolean;
  provisioned_at: string | null;
  usage: ServiceUsageData | null;
}

/** Usage data returned from the usage/summary endpoint. */
interface ServiceUsageData {
  service_name: string;
  tier: string;
  period_start: string;
  period_end: string;
  metrics: Record<string, unknown>;
  fetched_at: string;
}

/** Aggregated usage summary across all services. */
interface UsageSummary {
  services: ServiceUsageData[];
  total_monthly_cost_cents: number;
  bundle_savings_cents: number;
}

/** Response from the provision endpoint. */
interface ProvisionResponse {
  integration_id: string;
  service_name: string;
  service_user_id: string;
  tier: string;
  dashboard_url: string;
  provisioned_at: string;
}

// ---------------------------------------------------------------------------
// Icon mapping
// ---------------------------------------------------------------------------

/**
 * Maps backend icon string keys to Lucide React icon components.
 *
 * @param iconKey - The icon identifier from the service catalog (e.g. "search").
 * @returns The corresponding Lucide icon component, or Sparkles as fallback.
 */
const SERVICE_ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  search: Search,
  pencil: Pencil,
  "trending-up": TrendingUp,
  mail: Mail,
  eye: Eye,
  "share-2": Share2,
  target: Target,
  "message-circle": MessageCircle,
};

/**
 * Resolve a backend icon key to a React icon component.
 *
 * @param iconKey - The icon string from the service catalog.
 * @returns A Lucide React icon component.
 */
function getServiceIcon(iconKey: string): React.ComponentType<{ className?: string }> {
  return SERVICE_ICON_MAP[iconKey] ?? Sparkles;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Services Hub page component.
 *
 * Renders a header with usage summary, then a staggered grid of service cards.
 * Each card shows connection status, tier, and action buttons.
 *
 * @returns The services hub page wrapped in PageTransition.
 */
export default function ServicesHubPage() {
  const { user, loading: authLoading } = useAuth();
  const { store } = useStore();
  const storeId = store?.id;

  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [usageSummary, setUsageSummary] = useState<UsageSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Bridge health summary state
  const [bridgeSummary, setBridgeSummary] = useState<ServiceSummary[]>([]);

  // Enable dialog state
  const [enableDialogOpen, setEnableDialogOpen] = useState(false);
  const [selectedService, setSelectedService] = useState<ServiceStatus | null>(null);
  const [provisioning, setProvisioning] = useState(false);
  const [provisionError, setProvisionError] = useState<string | null>(null);

  /**
   * Fetch all services with user's connection status and usage summary.
   * Called on mount and after provisioning a service.
   */
  const fetchData = useCallback(async () => {
    const [servicesRes, usageRes, summaryRes] = await Promise.all([
      api.get<ServiceStatus[]>("/api/v1/services"),
      api.get<UsageSummary>("/api/v1/services/usage/summary"),
      api.get<ServiceSummary[]>("/api/v1/bridge/summary"),
    ]);

    if (servicesRes.error) {
      setError(servicesRes.error.message);
      setLoading(false);
      return;
    }

    setServices(servicesRes.data ?? []);
    if (usageRes.data) setUsageSummary(usageRes.data);
    if (summaryRes.data) setBridgeSummary(summaryRes.data);
    setLoading(false);
  }, []);

  useEffect(() => {
    if (authLoading || !user) return;
    fetchData();
  }, [user, authLoading, fetchData]);

  /**
   * Open the enable confirmation dialog for a service.
   *
   * @param svc - The service to enable.
   */
  function handleEnableClick(svc: ServiceStatus) {
    setSelectedService(svc);
    setProvisionError(null);
    setEnableDialogOpen(true);
  }

  /**
   * Provision the selected service on the free tier.
   * Calls POST /api/v1/services/{name}/provision and refreshes the list.
   */
  async function handleConfirmEnable() {
    if (!selectedService) return;
    setProvisioning(true);
    setProvisionError(null);

    const result = await api.post<ProvisionResponse>(
      `/api/v1/services/${selectedService.service.name}/provision`,
      {
        service_name: selectedService.service.name,
        tier: "free",
      }
    );

    if (result.error) {
      setProvisionError(result.error.message);
      setProvisioning(false);
      return;
    }

    setProvisioning(false);
    setEnableDialogOpen(false);
    setSelectedService(null);
    // Refresh list to show updated state
    await fetchData();
  }

  // Derived stats
  const connectedCount = services.filter((s) => s.is_connected).length;
  const totalServices = services.length;
  const monthlyCostDollars = usageSummary
    ? (usageSummary.total_monthly_cost_cents / 100).toFixed(2)
    : "0.00";

  // Loading skeleton
  if (loading) {
    return (
      <div className="mx-auto max-w-6xl p-6 space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-20 w-full rounded-xl" />
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-52 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <PageTransition>
      <main className="mx-auto max-w-6xl p-6 space-y-6">
        {/* Page Header */}
        <FadeIn>
          <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-2xl font-heading font-bold flex items-center gap-2">
                <Zap className="size-6 text-primary" />
                AI &amp; Automation
              </h1>
              <p className="text-sm text-muted-foreground mt-1">
                Connect AI-powered tools to supercharge your dropshipping business
              </p>
            </div>
            <Badge variant="outline" className="w-fit text-xs font-mono">
              {connectedCount}/{totalServices} connected
            </Badge>
          </div>
        </FadeIn>

        {/* Usage Summary Bar */}
        <FadeIn delay={0.1}>
          <Card variant="glass">
            <CardContent className="pt-5 pb-4">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <div className="size-2 rounded-full bg-emerald-500" />
                    <span className="text-sm font-medium">
                      {connectedCount} active {connectedCount === 1 ? "service" : "services"}
                    </span>
                  </div>
                  <div className="h-4 w-px bg-border" />
                  <span className="text-sm text-muted-foreground">
                    ${monthlyCostDollars}/mo total
                  </span>
                  {usageSummary && usageSummary.bundle_savings_cents > 0 && (
                    <>
                      <div className="h-4 w-px bg-border" />
                      <Badge variant="success" className="text-xs">
                        Saving ${(usageSummary.bundle_savings_cents / 100).toFixed(2)}/mo
                      </Badge>
                    </>
                  )}
                </div>
                {/* Connection progress bar */}
                <div className="flex items-center gap-2 min-w-[180px]">
                  <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full bg-primary transition-all duration-500"
                      style={{ width: `${totalServices > 0 ? (connectedCount / totalServices) * 100 : 0}%` }}
                    />
                  </div>
                  <span className="text-xs text-muted-foreground font-mono w-8 text-right">
                    {totalServices > 0 ? Math.round((connectedCount / totalServices) * 100) : 0}%
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </FadeIn>

        {/* Error State */}
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

        {/* Services Grid */}
        <StaggerChildren className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {services.map((svc) => {
            const summary = bridgeSummary.find(
              (s) => s.service_name === svc.service.name
            );
            return (
              <ServiceCard
                key={svc.service.name}
                svc={svc}
                storeId={storeId ?? ""}
                onEnable={() => handleEnableClick(svc)}
                bridgeSummary={summary ?? null}
              />
            );
          })}
        </StaggerChildren>

        {/* Enable Confirmation Dialog */}
        <Dialog open={enableDialogOpen} onOpenChange={setEnableDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                Enable {selectedService?.service.display_name}?
              </DialogTitle>
              <DialogDescription>
                {selectedService?.service.description}. You&apos;ll start on the
                free tier and can upgrade anytime.
              </DialogDescription>
            </DialogHeader>
            {provisionError && (
              <p className="text-sm text-destructive">{provisionError}</p>
            )}
            {selectedService && (
              <div className="rounded-lg border p-3 bg-muted/30">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                  Free tier includes
                </p>
                <ul className="space-y-1">
                  {selectedService.service.tiers
                    .find((t) => t.tier === "free")
                    ?.features.map((f) => (
                      <li key={f} className="text-sm flex items-center gap-2">
                        <CircleDot className="size-3 text-primary shrink-0" />
                        {f}
                      </li>
                    ))}
                </ul>
              </div>
            )}
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setEnableDialogOpen(false)}
                disabled={provisioning}
              >
                Cancel
              </Button>
              <Button
                onClick={handleConfirmEnable}
                disabled={provisioning}
              >
                {provisioning ? "Connecting..." : "Enable Service"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </main>
    </PageTransition>
  );
}

// ---------------------------------------------------------------------------
// Service Card Sub-component
// ---------------------------------------------------------------------------

/**
 * Props for the ServiceCard component.
 */
interface ServiceCardProps {
  /** The service status data to render. */
  svc: ServiceStatus;
  /** Current store ID for building detail links. */
  storeId: string;
  /** Callback fired when the "Enable" button is clicked. */
  onEnable: () => void;
  /** Bridge health summary for this service, if available. */
  bridgeSummary: ServiceSummary | null;
}

/**
 * Renders a single service as a card with brand color accent, status indicator,
 * and action buttons.
 *
 * Connected services show the current tier badge, a usage preview, and
 * "Open Dashboard" / "Details" buttons.
 * Disconnected services show the tagline and an "Enable" button.
 *
 * @param svc - The service status data.
 * @param storeId - The current store ID.
 * @param onEnable - Handler for the "Enable" button click.
 * @returns A motion.div card element.
 */
function ServiceCard({ svc, storeId, onEnable, bridgeSummary }: ServiceCardProps) {
  const { service, is_connected, current_tier } = svc;
  const Icon = getServiceIcon(service.icon);

  const currentTierInfo = service.tiers.find((t) => t.tier === current_tier);
  const priceDollars = currentTierInfo
    ? (currentTierInfo.price_monthly_cents / 100).toFixed(2)
    : "0.00";

  return (
    <motion.div
      variants={staggerItem}
      className="group"
    >
      <Card className="relative overflow-hidden h-full transition-shadow hover:shadow-md">
        {/* Brand color accent strip */}
        <div
          className="absolute inset-y-0 left-0 w-1 rounded-l-xl"
          style={{ backgroundColor: service.color }}
        />

        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              {/* Icon with brand-colored background */}
              <div
                className="flex size-9 items-center justify-center rounded-lg"
                style={{ backgroundColor: `${service.color}15` }}
              >
                <span style={{ color: service.color }}>
                  <Icon className="size-4.5" />
                </span>
              </div>
              <div className="min-w-0">
                <CardTitle className="text-sm font-heading leading-tight truncate">
                  {service.display_name}
                </CardTitle>
                <CardDescription className="text-xs mt-0.5 line-clamp-1">
                  {service.tagline}
                </CardDescription>
              </div>
            </div>

            {/* Connection status dot */}
            {is_connected && (
              <div className="flex items-center gap-1.5 shrink-0" title="Connected">
                <div className="size-2 rounded-full bg-emerald-500 animate-pulse" />
              </div>
            )}
          </div>
        </CardHeader>

        <CardContent className="pt-0 pb-4 space-y-3">
          {is_connected ? (
            /* Connected state */
            <>
              <div className="flex items-center gap-2">
                <Badge
                  variant="secondary"
                  className="text-xs capitalize"
                >
                  {current_tier ?? "free"} tier
                </Badge>
                {currentTierInfo && currentTierInfo.price_monthly_cents > 0 && (
                  <span className="text-xs text-muted-foreground font-mono">
                    ${priceDollars}/mo
                  </span>
                )}
              </div>

              {/* Bridge health indicator */}
              {bridgeSummary && (
                <div className="flex items-center gap-2 text-[11px]">
                  <div
                    className={`size-1.5 rounded-full shrink-0 ${
                      bridgeSummary.last_success === true
                        ? "bg-emerald-500"
                        : bridgeSummary.last_success === false
                          ? "bg-red-500"
                          : "bg-muted-foreground/30"
                    }`}
                  />
                  <span className="text-muted-foreground truncate">
                    {bridgeSummary.last_event_at
                      ? `Last event ${formatRelativeTime(bridgeSummary.last_event_at)}`
                      : "No events yet"}
                  </span>
                  {bridgeSummary.failure_count_24h > 0 && (
                    <Badge variant="destructive" className="text-[9px] px-1 py-0 h-4">
                      {bridgeSummary.failure_count_24h} fail
                    </Badge>
                  )}
                </div>
              )}

              <div className="flex gap-2">
                <a
                  href={service.dashboard_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1"
                >
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full gap-1.5 text-xs"
                  >
                    <ExternalLink className="size-3" />
                    Dashboard
                  </Button>
                </a>
                <Link href={`/stores/${storeId}/services/${service.name}`} className="flex-1">
                  <Button
                    variant="default"
                    size="sm"
                    className="w-full gap-1.5 text-xs"
                  >
                    Details
                    <ChevronRight className="size-3" />
                  </Button>
                </Link>
              </div>
            </>
          ) : (
            /* Disconnected state */
            <>
              <p className="text-xs text-muted-foreground line-clamp-2">
                {service.description}
              </p>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1 text-xs"
                  onClick={onEnable}
                >
                  Enable
                </Button>
                <Link href={`/stores/${storeId}/services/${service.name}`} className="flex-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full gap-1 text-xs text-muted-foreground"
                  >
                    Learn more
                    <ChevronRight className="size-3" />
                  </Button>
                </Link>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
