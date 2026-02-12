/**
 * Service detail page -- view and manage a single AI & Automation service.
 *
 * Shows service info, current plan, usage metrics, quick actions (open
 * dashboard, disconnect), and available plan tiers with upgrade buttons.
 *
 * **For Developers:**
 *   - The `[service]` param is the service name slug (e.g. "trendscout").
 *   - Fetches `GET /api/v1/services` for all services, then filters locally
 *     to find the one matching the URL param. This avoids needing a dedicated
 *     single-service endpoint.
 *   - Usage data comes from `GET /api/v1/services/{name}/usage` (only for
 *     connected services).
 *   - Disconnect calls `DELETE /api/v1/services/{name}`.
 *   - Upgrade calls `POST /api/v1/services/{name}/upgrade`.
 *   - Provision calls `POST /api/v1/services/{name}/provision`.
 *
 * **For QA Engineers:**
 *   - Navigating to an invalid service name shows "Service not found".
 *   - Connected services display: plan card with tier badge, usage metrics
 *     section, "Open Dashboard" external link, and "Disconnect" button.
 *   - Disconnecting shows a confirmation dialog and calls DELETE.
 *   - After disconnect, the page updates to show the "not connected" state.
 *   - The plan comparison section shows all tiers with a "Current" badge
 *     on the active tier and "Upgrade" buttons on higher tiers.
 *   - Upgrading triggers a POST and refreshes the page data.
 *   - Disconnected services show a prominent "Enable" CTA.
 *   - Usage metrics display keys formatted as human-readable labels.
 *
 * **For Project Managers:**
 *   This page gives users deep visibility into each connected service --
 *   their plan, usage, and available upgrades. It drives plan upsells and
 *   helps users understand what each AI tool provides.
 *
 * **For End Users:**
 *   View your current plan, see how much you've used this billing period,
 *   and upgrade or disconnect the service as needed.
 */

"use client";

import { useCallback, useEffect, useState, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Search,
  Pencil,
  TrendingUp,
  Mail,
  Eye,
  Share2,
  Target,
  MessageCircle,
  Sparkles,
  ExternalLink,
  ArrowLeft,
  CircleDot,
  Check,
  Unplug,
  ArrowUpRight,
  Shield,
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
  CardDescription,
  CardFooter,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

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

/** Usage data for a connected service. */
interface ServiceUsageData {
  service_name: string;
  tier: string;
  period_start: string;
  period_end: string;
  metrics: Record<string, unknown>;
  fetched_at: string;
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

/** Response from the upgrade endpoint. */
interface UpgradeResponse {
  service_name: string;
  old_tier: string;
  new_tier: string;
  message: string;
}

// ---------------------------------------------------------------------------
// Icon mapping
// ---------------------------------------------------------------------------

/**
 * Maps backend icon string keys to Lucide React icon components.
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

/**
 * Tier ordering for UI comparison.
 * Higher values are better/more expensive tiers.
 */
const TIER_ORDER: Record<string, number> = {
  free: 0,
  starter: 1,
  growth: 2,
  pro: 3,
  enterprise: 4,
};

/**
 * Format a metric key from snake_case to Title Case.
 *
 * @param key - The metric key (e.g. "products_researched").
 * @returns A human-readable label (e.g. "Products Researched").
 */
function formatMetricLabel(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Service detail page component.
 *
 * Shows the full information for a single service: header with brand color,
 * plan card, usage metrics, quick actions, and tier comparison.
 *
 * @returns The service detail page wrapped in PageTransition.
 */
export default function ServiceDetailPage({
  params,
}: {
  params: Promise<{ id: string; service: string }>;
}) {
  const { id: storeId, service: serviceName } = use(params);
  const { user, loading: authLoading } = useAuth();
  const { store } = useStore();
  const router = useRouter();

  const [svcStatus, setSvcStatus] = useState<ServiceStatus | null>(null);
  const [usage, setUsage] = useState<ServiceUsageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Action states
  const [disconnectDialogOpen, setDisconnectDialogOpen] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [enableDialogOpen, setEnableDialogOpen] = useState(false);
  const [provisioning, setProvisioning] = useState(false);
  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  /**
   * Fetch the service status and usage data.
   * Fetches all services and filters to find the one matching the URL param.
   */
  const fetchData = useCallback(async () => {
    setError(null);

    const servicesRes = await api.get<ServiceStatus[]>("/api/v1/services");
    if (servicesRes.error) {
      setError(servicesRes.error.message);
      setLoading(false);
      return;
    }

    const found = (servicesRes.data ?? []).find(
      (s) => s.service.name === serviceName
    );

    if (!found) {
      setNotFound(true);
      setLoading(false);
      return;
    }

    setSvcStatus(found);

    // Fetch usage if connected
    if (found.is_connected) {
      const usageRes = await api.get<ServiceUsageData>(
        `/api/v1/services/${serviceName}/usage`
      );
      if (usageRes.data) setUsage(usageRes.data);
    }

    setLoading(false);
  }, [serviceName]);

  useEffect(() => {
    if (authLoading || !user) return;
    fetchData();
  }, [user, authLoading, fetchData]);

  /**
   * Handle disconnecting the service.
   * Calls DELETE /api/v1/services/{name} and refreshes page data.
   */
  async function handleDisconnect() {
    setDisconnecting(true);
    setActionError(null);

    const result = await api.delete(`/api/v1/services/${serviceName}`);
    if (result.error) {
      setActionError(result.error.message);
      setDisconnecting(false);
      return;
    }

    setDisconnecting(false);
    setDisconnectDialogOpen(false);
    setUsage(null);
    // Refresh to show disconnected state
    setLoading(true);
    await fetchData();
  }

  /**
   * Handle enabling (provisioning) the service on the free tier.
   * Calls POST /api/v1/services/{name}/provision and refreshes.
   */
  async function handleEnable() {
    setProvisioning(true);
    setActionError(null);

    const result = await api.post<ProvisionResponse>(
      `/api/v1/services/${serviceName}/provision`,
      { service_name: serviceName, tier: "free" }
    );

    if (result.error) {
      setActionError(result.error.message);
      setProvisioning(false);
      return;
    }

    setProvisioning(false);
    setEnableDialogOpen(false);
    setLoading(true);
    await fetchData();
  }

  /**
   * Handle upgrading to a new tier.
   * Calls POST /api/v1/services/{name}/upgrade and refreshes.
   *
   * @param tier - The target tier to upgrade to.
   */
  async function handleUpgrade(tier: string) {
    setUpgrading(tier);
    setActionError(null);

    const result = await api.post<UpgradeResponse>(
      `/api/v1/services/${serviceName}/upgrade`,
      { tier }
    );

    if (result.error) {
      setActionError(result.error.message);
      setUpgrading(null);
      return;
    }

    setUpgrading(null);
    setLoading(true);
    await fetchData();
  }

  // Loading skeleton
  if (loading) {
    return (
      <div className="mx-auto max-w-4xl p-6 space-y-6">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-32 w-full rounded-xl" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Skeleton className="h-48 rounded-xl" />
          <Skeleton className="h-48 rounded-xl" />
          <Skeleton className="h-48 rounded-xl" />
        </div>
      </div>
    );
  }

  // Not found state
  if (notFound) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-20">
        <h2 className="font-heading text-xl font-semibold">Service not found</h2>
        <p className="text-muted-foreground">
          The service &quot;{serviceName}&quot; does not exist in the catalog.
        </p>
        <Link href={`/stores/${storeId}/services`}>
          <Button variant="outline">Back to Services</Button>
        </Link>
      </div>
    );
  }

  if (!svcStatus) return null;

  const { service, is_connected, current_tier, provisioned_at } = svcStatus;
  const Icon = getServiceIcon(service.icon);
  const currentTierInfo = service.tiers.find((t) => t.tier === current_tier);
  const currentTierOrder = TIER_ORDER[current_tier ?? "free"] ?? 0;

  return (
    <PageTransition>
      <main className="mx-auto max-w-4xl p-6 space-y-6">
        {/* Back Navigation */}
        <FadeIn>
          <Link
            href={`/stores/${storeId}/services`}
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="size-4" />
            Back to Services
          </Link>
        </FadeIn>

        {/* Service Header */}
        <FadeIn delay={0.05}>
          <Card className="relative overflow-hidden">
            {/* Brand color top bar */}
            <div
              className="absolute inset-x-0 top-0 h-1"
              style={{ backgroundColor: service.color }}
            />

            <CardHeader className="pt-8">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div className="flex items-center gap-4">
                  <div
                    className="flex size-12 items-center justify-center rounded-xl"
                    style={{ backgroundColor: `${service.color}15` }}
                  >
                    <span style={{ color: service.color }}>
                      <Icon className="size-6" />
                    </span>
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <CardTitle className="text-xl font-heading">
                        {service.display_name}
                      </CardTitle>
                      {is_connected && (
                        <Badge variant="success" className="text-xs">
                          Connected
                        </Badge>
                      )}
                    </div>
                    <CardDescription className="mt-1">
                      {service.tagline}
                    </CardDescription>
                  </div>
                </div>

                {is_connected && (
                  <div className="flex gap-2 shrink-0">
                    <a
                      href={service.dashboard_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <Button variant="default" size="sm" className="gap-1.5">
                        <ExternalLink className="size-3.5" />
                        Open Dashboard
                      </Button>
                    </a>
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-1.5 text-destructive hover:text-destructive"
                      onClick={() => {
                        setActionError(null);
                        setDisconnectDialogOpen(true);
                      }}
                    >
                      <Unplug className="size-3.5" />
                      Disconnect
                    </Button>
                  </div>
                )}
              </div>
            </CardHeader>

            <CardContent className="pb-5">
              <p className="text-sm text-muted-foreground">
                {service.description}
              </p>
              {is_connected && provisioned_at && (
                <p className="text-xs text-muted-foreground mt-2">
                  Connected since {new Date(provisioned_at).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })}
                </p>
              )}
            </CardContent>
          </Card>
        </FadeIn>

        {/* Action Error Banner */}
        {actionError && (
          <FadeIn>
            <Card className="border-destructive/50">
              <CardContent className="pt-5 pb-4">
                <p className="text-sm text-destructive">{actionError}</p>
              </CardContent>
            </Card>
          </FadeIn>
        )}

        {/* Error Banner */}
        {error && (
          <FadeIn>
            <Card className="border-destructive/50">
              <CardContent className="pt-5 pb-4">
                <p className="text-sm text-destructive">{error}</p>
              </CardContent>
            </Card>
          </FadeIn>
        )}

        {/* Not Connected -- Enable CTA */}
        {!is_connected && (
          <FadeIn delay={0.1}>
            <Card className="border-dashed border-2">
              <CardContent className="flex flex-col items-center justify-center py-10 gap-4">
                <div
                  className="flex size-16 items-center justify-center rounded-2xl"
                  style={{ backgroundColor: `${service.color}15` }}
                >
                  <span style={{ color: service.color }}>
                    <Icon className="size-8" />
                  </span>
                </div>
                <div className="text-center space-y-1">
                  <h3 className="font-heading font-semibold">
                    Get started with {service.display_name}
                  </h3>
                  <p className="text-sm text-muted-foreground max-w-md">
                    Connect this service to unlock {service.tagline.toLowerCase()}{" "}
                    capabilities. Start free, upgrade when you need more.
                  </p>
                </div>
                <Button
                  size="lg"
                  onClick={() => {
                    setActionError(null);
                    setEnableDialogOpen(true);
                  }}
                  className="gap-2"
                >
                  <Sparkles className="size-4" />
                  Enable {service.display_name}
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        )}

        {/* Current Plan (connected only) */}
        {is_connected && currentTierInfo && (
          <FadeIn delay={0.1}>
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-heading">Current Plan</CardTitle>
                  <Badge variant="outline" className="text-xs capitalize font-mono">
                    {currentTierInfo.name}
                  </Badge>
                </div>
                <CardDescription>
                  {currentTierInfo.price_monthly_cents === 0
                    ? "Free"
                    : `$${(currentTierInfo.price_monthly_cents / 100).toFixed(2)}/month`}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-1.5">
                  {currentTierInfo.features.map((feature) => (
                    <li
                      key={feature}
                      className="text-sm flex items-center gap-2"
                    >
                      <span className="shrink-0" style={{ color: service.color }}>
                        <Check className="size-3.5" />
                      </span>
                      {feature}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </FadeIn>
        )}

        {/* Usage Metrics (connected only) */}
        {is_connected && usage && Object.keys(usage.metrics).length > 0 && (
          <FadeIn delay={0.15}>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-heading">
                  Usage This Period
                </CardTitle>
                <CardDescription>
                  {new Date(usage.period_start).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                  })}{" "}
                  &ndash;{" "}
                  {new Date(usage.period_end).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {Object.entries(usage.metrics).map(([key, value]) => (
                    <div
                      key={key}
                      className="rounded-lg border p-3 bg-muted/20"
                    >
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        {formatMetricLabel(key)}
                      </p>
                      <p className="text-lg font-bold mt-1 font-mono">
                        {typeof value === "number"
                          ? value.toLocaleString()
                          : String(value)}
                      </p>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground mt-3">
                  Last updated{" "}
                  {new Date(usage.fetched_at).toLocaleTimeString("en-US", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
              </CardContent>
            </Card>
          </FadeIn>
        )}

        {/* Plan Tiers Comparison */}
        <FadeIn delay={0.2}>
          <div className="space-y-3">
            <h2 className="text-lg font-heading font-semibold">Available Plans</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {service.tiers.map((tier) => {
                const isCurrent = is_connected && tier.tier === current_tier;
                const tierOrder = TIER_ORDER[tier.tier] ?? 0;
                const canUpgrade = is_connected && tierOrder > currentTierOrder;

                return (
                  <Card
                    key={tier.tier}
                    className={
                      isCurrent
                        ? "ring-2 ring-primary"
                        : "border-border"
                    }
                  >
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm font-heading">
                          {tier.name}
                        </CardTitle>
                        {isCurrent && (
                          <Badge variant="default" className="text-xs">
                            Current
                          </Badge>
                        )}
                      </div>
                      <CardDescription className="font-mono">
                        {tier.price_monthly_cents === 0
                          ? "Free"
                          : `$${(tier.price_monthly_cents / 100).toFixed(2)}/mo`}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <ul className="space-y-1.5">
                        {tier.features.map((feature) => (
                          <li
                            key={feature}
                            className="text-sm flex items-start gap-2"
                          >
                            <CircleDot className="size-3 mt-1 shrink-0 text-muted-foreground" />
                            {feature}
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                    <CardFooter>
                      {isCurrent ? (
                        <Button variant="outline" size="sm" className="w-full" disabled>
                          <Shield className="size-3.5 mr-1.5" />
                          Current Plan
                        </Button>
                      ) : canUpgrade ? (
                        <Button
                          variant="default"
                          size="sm"
                          className="w-full gap-1.5"
                          disabled={upgrading === tier.tier}
                          onClick={() => handleUpgrade(tier.tier)}
                        >
                          {upgrading === tier.tier ? (
                            "Upgrading..."
                          ) : (
                            <>
                              <ArrowUpRight className="size-3.5" />
                              Upgrade
                            </>
                          )}
                        </Button>
                      ) : !is_connected ? (
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full"
                          onClick={() => {
                            setActionError(null);
                            setEnableDialogOpen(true);
                          }}
                        >
                          Enable on {tier.name}
                        </Button>
                      ) : (
                        <Button variant="ghost" size="sm" className="w-full" disabled>
                          Included in higher tier
                        </Button>
                      )}
                    </CardFooter>
                  </Card>
                );
              })}
            </div>
          </div>
        </FadeIn>

        {/* Disconnect Confirmation Dialog */}
        <Dialog open={disconnectDialogOpen} onOpenChange={setDisconnectDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                Disconnect {service.display_name}?
              </DialogTitle>
              <DialogDescription>
                This will deactivate your connection to {service.display_name}.
                Your data will be preserved for 30 days in case you want to
                reconnect. Any active subscription will be cancelled.
              </DialogDescription>
            </DialogHeader>
            {actionError && (
              <p className="text-sm text-destructive">{actionError}</p>
            )}
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setDisconnectDialogOpen(false)}
                disabled={disconnecting}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleDisconnect}
                disabled={disconnecting}
              >
                {disconnecting ? "Disconnecting..." : "Disconnect"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Enable Confirmation Dialog */}
        <Dialog open={enableDialogOpen} onOpenChange={setEnableDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                Enable {service.display_name}?
              </DialogTitle>
              <DialogDescription>
                {service.description}. You&apos;ll start on the free tier and
                can upgrade anytime.
              </DialogDescription>
            </DialogHeader>
            {actionError && (
              <p className="text-sm text-destructive">{actionError}</p>
            )}
            <div className="rounded-lg border p-3 bg-muted/30">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                Free tier includes
              </p>
              <ul className="space-y-1">
                {service.tiers
                  .find((t) => t.tier === "free")
                  ?.features.map((f) => (
                    <li key={f} className="text-sm flex items-center gap-2">
                      <CircleDot className="size-3 text-primary shrink-0" />
                      {f}
                    </li>
                  ))}
              </ul>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setEnableDialogOpen(false)}
                disabled={provisioning}
              >
                Cancel
              </Button>
              <Button
                onClick={handleEnable}
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
