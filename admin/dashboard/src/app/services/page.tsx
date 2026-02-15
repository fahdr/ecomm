/**
 * Services overview page for the Super Admin Dashboard.
 *
 * Displays a grid of all platform services (8 SaaS products +
 * the LLM Gateway) with their current health status, port, and
 * uptime information.
 *
 * For Developers:
 *   API endpoint used:
 *     GET /services — returns list of services with health data
 *   Falls back to a hardcoded service list if the endpoint is
 *   unavailable, marking all services as "unknown".
 *
 * For QA Engineers:
 *   - Verify all 9 services appear in the grid.
 *   - Verify status badges show correct colors.
 *   - Verify port numbers are correct.
 *   - Verify loading skeletons appear during fetch.
 *
 * For Project Managers:
 *   This page gives admins visibility into which services are
 *   running and healthy across the entire platform.
 *
 * For End Users:
 *   This page is exclusively for platform administrators.
 */

"use client";

import { useEffect, useState } from "react";
import {
  Server,
  ExternalLink,
  RefreshCw,
  Clock,
} from "lucide-react";
import * as motion from "motion/react-client";
import { AdminShell } from "@/components/admin-shell";
import { StatusBadge, type HealthStatus } from "@/components/status-badge";
import { adminApi } from "@/lib/api";

/**
 * Shape of a service entry from the admin API.
 */
interface ServiceInfo {
  name: string;
  display_name: string;
  status: HealthStatus;
  port: number;
  dashboard_port?: number;
  description?: string;
  uptime?: string;
  version?: string;
  url?: string;
}

/**
 * Default service registry — the complete list of platform services.
 *
 * Used as fallback when the API is unreachable or doesn't return
 * all expected services. Port assignments match the platform
 * architecture documentation.
 */
const SERVICE_REGISTRY: ServiceInfo[] = [
  {
    name: "llm-gateway",
    display_name: "LLM Gateway",
    status: "unknown",
    port: 8200,
    description: "Centralized AI inference proxy for all services",
  },
  {
    name: "core-platform",
    display_name: "Core Platform",
    status: "unknown",
    port: 8000,
    dashboard_port: 3000,
    description: "Main dropshipping platform backend and dashboard",
  },
  {
    name: "shopchat",
    display_name: "ShopChat",
    status: "unknown",
    port: 8101,
    dashboard_port: 3101,
    description: "AI-powered customer support chatbot",
  },
  {
    name: "contentforge",
    display_name: "ContentForge",
    status: "unknown",
    port: 8102,
    dashboard_port: 3102,
    description: "AI product description and content generator",
  },
  {
    name: "adscale",
    display_name: "AdScale",
    status: "unknown",
    port: 8103,
    dashboard_port: 3103,
    description: "AI-driven ad copy and campaign optimizer",
  },
  {
    name: "rankpilot",
    display_name: "RankPilot",
    status: "unknown",
    port: 8104,
    dashboard_port: 3104,
    description: "SEO analysis and optimization tool",
  },
  {
    name: "spydrop",
    display_name: "SpyDrop",
    status: "unknown",
    port: 8105,
    dashboard_port: 3105,
    description: "Competitor analysis and market intelligence",
  },
  {
    name: "trendscout",
    display_name: "TrendScout",
    status: "unknown",
    port: 8106,
    dashboard_port: 3106,
    description: "Trending product and niche discovery",
  },
  {
    name: "flowsend",
    display_name: "FlowSend",
    status: "unknown",
    port: 8107,
    dashboard_port: 3107,
    description: "Email marketing automation platform",
  },
  {
    name: "postpilot",
    display_name: "PostPilot",
    status: "unknown",
    port: 8108,
    dashboard_port: 3108,
    description: "Social media content scheduler and manager",
  },
];

/**
 * Services overview page component.
 *
 * Renders a grid of service cards with health status, ports,
 * and descriptions. Supports manual refresh.
 *
 * @returns The services page JSX.
 */
export default function ServicesPage() {
  /** Service data (merged from API response and defaults). */
  const [services, setServices] = useState<ServiceInfo[]>(SERVICE_REGISTRY);

  /** Loading state for data fetch. */
  const [loading, setLoading] = useState(true);

  /** Whether a manual refresh is in progress. */
  const [refreshing, setRefreshing] = useState(false);

  /**
   * Fetch service health data from the admin API.
   *
   * Merges API response with the default registry to ensure
   * all expected services are displayed.
   */
  const fetchServices = async () => {
    try {
      const data = await adminApi.get<{ services: ServiceInfo[] }>("/services");
      if (data?.services) {
        /* Merge API data into the default registry. */
        const merged = SERVICE_REGISTRY.map((defaultSvc) => {
          const apiSvc = data.services.find((s) => s.name === defaultSvc.name);
          return apiSvc
            ? { ...defaultSvc, ...apiSvc }
            : defaultSvc;
        });

        /* Add any services from the API that aren't in the registry. */
        const extraServices = data.services.filter(
          (s) => !SERVICE_REGISTRY.some((d) => d.name === s.name)
        );

        setServices([...merged, ...extraServices]);
      }
    } catch {
      /* Fall back to defaults with unknown status. */
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  /** Fetch on mount. */
  useEffect(() => {
    fetchServices();
  }, []);

  /**
   * Handle manual refresh button click.
   */
  const handleRefresh = () => {
    setRefreshing(true);
    fetchServices();
  };

  /** Count of services by status. */
  const healthyCount = services.filter((s) => s.status === "healthy").length;
  const degradedCount = services.filter((s) => s.status === "degraded").length;
  const downCount = services.filter((s) => s.status === "down").length;

  return (
    <AdminShell>
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Page header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="flex items-center justify-between"
        >
          <div>
            <div className="flex items-center gap-3 mb-1">
              <Server size={20} className="text-[var(--admin-primary)]" />
              <h1 className="text-lg font-semibold text-[var(--admin-text-primary)]">
                Services
              </h1>
            </div>
            <p className="text-sm text-[var(--admin-text-muted)]">
              Platform service health and configuration
            </p>
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="admin-btn-ghost flex items-center gap-2"
          >
            <RefreshCw
              size={14}
              className={refreshing ? "animate-spin" : ""}
            />
            Refresh
          </button>
        </motion.div>

        {/* Health summary bar */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="admin-card p-4 flex items-center gap-6"
        >
          <div className="flex items-center gap-2">
            <span className="text-xs text-[var(--admin-text-muted)] uppercase tracking-wider">
              Total
            </span>
            <span className="font-data text-sm font-bold text-[var(--admin-text-primary)]">
              {services.length}
            </span>
          </div>
          <div className="w-px h-5 bg-[var(--admin-border)]" />
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[var(--admin-success)]" />
            <span className="font-data text-sm text-[var(--admin-success)]">
              {healthyCount}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[var(--admin-accent)]" />
            <span className="font-data text-sm text-[var(--admin-accent)]">
              {degradedCount}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[var(--admin-danger)]" />
            <span className="font-data text-sm text-[var(--admin-danger)]">
              {downCount}
            </span>
          </div>
        </motion.div>

        {/* Service grid */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 9 }).map((_, i) => (
              <div
                key={i}
                className="admin-card p-5 h-36 animate-pulse bg-[var(--admin-bg-surface)]"
              />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {services.map((service, index) => (
              <motion.div
                key={service.name}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, delay: 0.04 * index }}
                className="admin-card p-5"
              >
                {/* Service header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold text-[var(--admin-text-primary)] truncate">
                      {service.display_name}
                    </h3>
                    <p className="font-data text-[11px] text-[var(--admin-text-muted)]">
                      {service.name}
                    </p>
                  </div>
                  <StatusBadge status={service.status} size="sm" />
                </div>

                {/* Description */}
                {service.description && (
                  <p className="text-xs text-[var(--admin-text-muted)] mb-3 line-clamp-2">
                    {service.description}
                  </p>
                )}

                {/* Port and meta info */}
                <div className="flex items-center gap-4 text-[11px] text-[var(--admin-text-muted)]">
                  <div className="flex items-center gap-1">
                    <ExternalLink size={10} />
                    <span className="font-data">:{service.port}</span>
                  </div>
                  {service.dashboard_port && (
                    <div className="flex items-center gap-1">
                      <ExternalLink size={10} />
                      <span className="font-data">
                        :{service.dashboard_port}
                      </span>
                    </div>
                  )}
                  {service.uptime && (
                    <div className="flex items-center gap-1">
                      <Clock size={10} />
                      <span className="font-data">{service.uptime}</span>
                    </div>
                  )}
                  {service.version && (
                    <span className="font-data">v{service.version}</span>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </AdminShell>
  );
}
