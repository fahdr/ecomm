/**
 * SEO Audits page -- run audits and view historical results.
 *
 * Allows users to select a site, trigger an SEO audit, and browse previous
 * audit results with scores, issue counts, and detailed breakdowns.
 *
 * **For Developers:**
 *   - `GET /api/v1/sites` -- fetch sites for the site selector dropdown.
 *   - `POST /api/v1/audits/run` -- run a new audit `{ site_id }`.
 *   - `GET /api/v1/audits?site_id=...` -- list audit history (paginated).
 *   - `GET /api/v1/audits/:id` -- get a single audit with full detail.
 *   - Audits are read-only after creation. There is no update or delete endpoint.
 *
 * **For Project Managers:**
 *   - Audits are a primary engagement driver. Users can see SEO health
 *     improve over time as they fix issues, encouraging continued usage.
 *   - The score (0-100) provides a clear, gamified progress metric.
 *
 * **For QA Engineers:**
 *   - Verify loading skeletons during data fetch.
 *   - Test running an audit and confirming it appears in the history.
 *   - Test the score ring renders correctly for scores at 0, 50, and 100.
 *   - Test expanding an audit to view issues and recommendations.
 *   - Test with no sites -- should show a "create a site first" message.
 *   - Test with no audits -- should show an empty state with "Run your first audit".
 *
 * **For End Users:**
 *   - Select a site and click "Run Audit" to get an SEO health check.
 *   - Review your score, issues, and recommendations for improvement.
 *   - Track your progress by comparing audit scores over time.
 */

"use client";

import * as React from "react";
import {
  ClipboardCheck,
  Play,
  Loader2,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  CheckCircle2,
  Info,
  ArrowRight,
} from "lucide-react";
import { Shell } from "@/components/shell";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  FadeIn,
  StaggerChildren,
  PageTransition,
  AnimatedCounter,
} from "@/components/motion";
import { api } from "@/lib/api";

/** Shape of a site record (subset needed for the selector). */
interface Site {
  id: string;
  domain: string;
  is_verified: boolean;
}

/** Paginated response envelope for sites. */
interface PaginatedSites {
  items: Site[];
  total: number;
}

/** Shape of an issue within an audit result. */
interface AuditIssue {
  severity: string;
  category: string;
  message: string;
}

/** Shape of an SEO audit result. */
interface Audit {
  id: string;
  site_id: string;
  overall_score: number;
  issues: AuditIssue[];
  recommendations: string[];
  pages_crawled: number;
  created_at: string;
}

/** Paginated response envelope for audits. */
interface PaginatedAudits {
  items: Audit[];
  total: number;
  page: number;
  per_page: number;
}

/**
 * SEO Audits page component.
 *
 * @returns The audits page wrapped in the Shell layout.
 */
export default function AuditsPage() {
  /* Site selection */
  const [sites, setSites] = React.useState<Site[]>([]);
  const [selectedSiteId, setSelectedSiteId] = React.useState<string | null>(null);
  const [sitesLoading, setSitesLoading] = React.useState(true);

  /* Audits list */
  const [audits, setAudits] = React.useState<Audit[]>([]);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  /* Run audit state */
  const [running, setRunning] = React.useState(false);

  /* Expanded audit detail (ID) */
  const [expandedId, setExpandedId] = React.useState<string | null>(null);

  /**
   * Fetch all sites on mount for the site selector.
   */
  React.useEffect(() => {
    async function fetchSites() {
      const { data } = await api.get<PaginatedSites>("/api/v1/sites?per_page=100");
      if (data && data.items.length > 0) {
        setSites(data.items);
        setSelectedSiteId(data.items[0].id);
      }
      setSitesLoading(false);
    }
    fetchSites();
  }, []);

  /**
   * Fetch audits whenever the selected site changes.
   */
  React.useEffect(() => {
    if (selectedSiteId) {
      fetchAudits(selectedSiteId);
    }
  }, [selectedSiteId]);

  /**
   * Fetch the audit history for a site.
   *
   * @param siteId - The UUID of the site to fetch audits for.
   */
  async function fetchAudits(siteId: string) {
    setLoading(true);
    setError(null);
    const { data, error: apiError } = await api.get<PaginatedAudits>(
      `/api/v1/audits?site_id=${siteId}&per_page=50`
    );
    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setAudits(data.items);
      setTotal(data.total);
    }
    setLoading(false);
  }

  /**
   * Run a new SEO audit for the selected site.
   */
  async function handleRunAudit() {
    if (!selectedSiteId) return;

    setRunning(true);
    setError(null);

    const { error: apiError } = await api.post<Audit>("/api/v1/audits/run", {
      site_id: selectedSiteId,
    });
    setRunning(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    fetchAudits(selectedSiteId);
  }

  /**
   * Toggle expanded state for an audit row to show/hide details.
   *
   * @param auditId - The UUID of the audit to toggle.
   */
  function toggleExpanded(auditId: string) {
    setExpandedId((prev) => (prev === auditId ? null : auditId));
  }

  /**
   * Render a score ring (circular progress indicator) for an audit score.
   *
   * @param score - The audit score (0-100).
   * @returns An SVG circular progress ring with the score in the center.
   */
  function renderScoreRing(score: number) {
    const radius = 28;
    const circumference = 2 * Math.PI * radius;
    const progress = (score / 100) * circumference;
    const remaining = circumference - progress;

    /* Color based on score: green >= 80, amber 50-79, red < 50 */
    let strokeColor = "stroke-emerald-500";
    let textColor = "text-emerald-600 dark:text-emerald-400";
    if (score < 50) {
      strokeColor = "stroke-red-500";
      textColor = "text-red-600 dark:text-red-400";
    } else if (score < 80) {
      strokeColor = "stroke-amber-500";
      textColor = "text-amber-600 dark:text-amber-400";
    }

    return (
      <div className="relative size-16 shrink-0">
        <svg
          className="size-16 -rotate-90"
          viewBox="0 0 64 64"
          fill="none"
        >
          {/* Background track */}
          <circle
            cx="32"
            cy="32"
            r={radius}
            strokeWidth="5"
            className="stroke-muted"
          />
          {/* Progress arc */}
          <circle
            cx="32"
            cy="32"
            r={radius}
            strokeWidth="5"
            strokeLinecap="round"
            className={strokeColor}
            strokeDasharray={`${progress} ${remaining}`}
            style={{
              transition: "stroke-dasharray 0.8s ease-out",
            }}
          />
        </svg>
        <span
          className={`absolute inset-0 flex items-center justify-center text-sm font-bold tabular-nums ${textColor}`}
        >
          {score}
        </span>
      </div>
    );
  }

  /**
   * Render an issue severity badge.
   *
   * @param severity - The issue severity level (critical, warning, info).
   * @returns A Badge element with appropriate color.
   */
  function renderSeverityBadge(severity: string) {
    switch (severity.toLowerCase()) {
      case "critical":
        return (
          <Badge variant="destructive" className="text-xs">
            <AlertTriangle className="size-3 mr-1" />
            Critical
          </Badge>
        );
      case "warning":
        return (
          <Badge variant="secondary" className="text-xs bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400 border-transparent">
            <AlertTriangle className="size-3 mr-1" />
            Warning
          </Badge>
        );
      case "info":
      default:
        return (
          <Badge variant="outline" className="text-xs">
            <Info className="size-3 mr-1" />
            Info
          </Badge>
        );
    }
  }

  /**
   * Format a date string for display.
   *
   * @param dateStr - ISO date string.
   * @returns Formatted date with time.
   */
  function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  /* Selected site name for display */
  const selectedSite = sites.find((s) => s.id === selectedSiteId);

  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* -- Page Header -- */}
        <FadeIn direction="down">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight">
                SEO Audits
              </h2>
              <p className="text-muted-foreground mt-1">
                Run site audits and track your SEO health over time.
              </p>
            </div>
            {selectedSiteId && (
              <Button onClick={handleRunAudit} disabled={running}>
                {running ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Play className="size-4" />
                )}
                {running ? "Running..." : "Run Audit"}
              </Button>
            )}
          </div>
        </FadeIn>

        {/* -- Site Selector -- */}
        {sitesLoading ? (
          <Skeleton className="h-10 w-64" />
        ) : sites.length === 0 ? (
          <FadeIn>
            <Card>
              <CardContent className="pt-12 pb-12 text-center">
                <div className="mx-auto size-12 rounded-full bg-muted flex items-center justify-center mb-4">
                  <ClipboardCheck className="size-6 text-muted-foreground" />
                </div>
                <h3 className="font-heading font-semibold text-lg">
                  No sites registered
                </h3>
                <p className="text-muted-foreground text-sm mt-1 max-w-sm mx-auto">
                  Add a site first before you can run SEO audits.
                </p>
                <Button className="mt-4" asChild>
                  <a href="/sites">
                    <ArrowRight className="size-4" />
                    Go to Sites
                  </a>
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        ) : (
          <FadeIn>
            <div className="flex items-center gap-3">
              <label htmlFor="audit-site-select" className="text-sm font-medium whitespace-nowrap">
                Site:
              </label>
              <select
                id="audit-site-select"
                value={selectedSiteId || ""}
                onChange={(e) => setSelectedSiteId(e.target.value)}
                className="flex h-9 w-full max-w-xs rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {sites.map((site) => (
                  <option key={site.id} value={site.id}>
                    {site.domain}
                  </option>
                ))}
              </select>
            </div>
          </FadeIn>
        )}

        {/* -- Score Summary (latest audit) -- */}
        {selectedSiteId && !loading && audits.length > 0 && (
          <FadeIn delay={0.1}>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Card className="py-4">
                <CardContent className="flex items-center justify-center gap-4">
                  {renderScoreRing(audits[0].overall_score)}
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wide">
                      Latest Score
                    </p>
                    <p className="text-lg font-bold font-heading">
                      {audits[0].overall_score}/100
                    </p>
                  </div>
                </CardContent>
              </Card>
              <Card className="py-4">
                <CardContent className="text-center">
                  <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">
                    Issues Found
                  </p>
                  <AnimatedCounter
                    value={audits[0].issues.length}
                    className="text-2xl font-bold font-heading"
                  />
                </CardContent>
              </Card>
              <Card className="py-4">
                <CardContent className="text-center">
                  <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">
                    Total Audits
                  </p>
                  <AnimatedCounter
                    value={total}
                    className="text-2xl font-bold font-heading"
                  />
                </CardContent>
              </Card>
            </div>
          </FadeIn>
        )}

        {/* -- Audit History -- */}
        {selectedSiteId && (
          <>
            {loading ? (
              <div className="space-y-4">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Card key={i}>
                    <CardContent className="pt-6">
                      <div className="flex items-center gap-4">
                        <Skeleton className="size-16 rounded-full" />
                        <div className="flex-1 space-y-2">
                          <Skeleton className="h-4 w-40" />
                          <Skeleton className="h-3 w-56" />
                        </div>
                        <Skeleton className="h-8 w-24" />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : audits.length === 0 ? (
              <FadeIn>
                <Card>
                  <CardContent className="pt-12 pb-12 text-center">
                    <div className="mx-auto size-12 rounded-full bg-muted flex items-center justify-center mb-4">
                      <ClipboardCheck className="size-6 text-muted-foreground" />
                    </div>
                    <h3 className="font-heading font-semibold text-lg">
                      No audits yet
                    </h3>
                    <p className="text-muted-foreground text-sm mt-1 max-w-sm mx-auto">
                      Run your first SEO audit to get a health score and
                      actionable recommendations.
                    </p>
                    <Button
                      className="mt-4"
                      onClick={handleRunAudit}
                      disabled={running}
                    >
                      {running ? (
                        <Loader2 className="size-4 animate-spin" />
                      ) : (
                        <Play className="size-4" />
                      )}
                      Run your first audit
                    </Button>
                  </CardContent>
                </Card>
              </FadeIn>
            ) : (
              <div>
                <FadeIn delay={0.15}>
                  <h3 className="font-heading text-lg font-semibold mb-4">
                    Audit History
                  </h3>
                </FadeIn>
                <StaggerChildren className="space-y-3" staggerDelay={0.06}>
                  {audits.map((audit) => (
                    <Card key={audit.id} className="py-3 overflow-hidden">
                      {/* Collapsed Row */}
                      <CardContent>
                        <button
                          type="button"
                          className="w-full flex items-center gap-4 text-left"
                          onClick={() => toggleExpanded(audit.id)}
                        >
                          {/* Score Ring */}
                          {renderScoreRing(audit.overall_score)}

                          {/* Audit Summary */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <p className="text-sm font-medium">
                                Audit on {formatDate(audit.created_at)}
                              </p>
                              <Badge variant="outline" className="text-xs">
                                {audit.pages_crawled} pages
                              </Badge>
                            </div>
                            <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
                              <span>
                                {audit.issues.length} issue
                                {audit.issues.length !== 1 ? "s" : ""}
                              </span>
                              <span>
                                {audit.recommendations.length} recommendation
                                {audit.recommendations.length !== 1 ? "s" : ""}
                              </span>
                            </div>
                          </div>

                          {/* Expand Toggle */}
                          <div className="shrink-0">
                            {expandedId === audit.id ? (
                              <ChevronUp className="size-5 text-muted-foreground" />
                            ) : (
                              <ChevronDown className="size-5 text-muted-foreground" />
                            )}
                          </div>
                        </button>
                      </CardContent>

                      {/* Expanded Detail */}
                      {expandedId === audit.id && (
                        <div className="border-t bg-secondary/20 px-6 py-4 space-y-5">
                          {/* Issues Section */}
                          {audit.issues.length > 0 && (
                            <div>
                              <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                                <AlertTriangle className="size-4 text-amber-500" />
                                Issues ({audit.issues.length})
                              </h4>
                              <div className="space-y-2">
                                {audit.issues.map((issue, idx) => (
                                  <div
                                    key={idx}
                                    className="flex items-start gap-3 p-2 rounded-md bg-background border"
                                  >
                                    {renderSeverityBadge(issue.severity)}
                                    <div className="flex-1 min-w-0">
                                      <p className="text-sm">{issue.message}</p>
                                      <p className="text-xs text-muted-foreground mt-0.5">
                                        Category: {issue.category}
                                      </p>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Recommendations Section */}
                          {audit.recommendations.length > 0 && (
                            <div>
                              <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                                <CheckCircle2 className="size-4 text-emerald-500" />
                                Recommendations ({audit.recommendations.length})
                              </h4>
                              <ul className="space-y-2">
                                {audit.recommendations.map((rec, idx) => (
                                  <li
                                    key={idx}
                                    className="flex items-start gap-2 text-sm p-2 rounded-md bg-background border"
                                  >
                                    <span className="text-emerald-500 mt-0.5 shrink-0">
                                      {idx + 1}.
                                    </span>
                                    <span>{rec}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* No issues */}
                          {audit.issues.length === 0 &&
                            audit.recommendations.length === 0 && (
                              <p className="text-sm text-muted-foreground text-center py-4">
                                No issues or recommendations for this audit.
                              </p>
                            )}
                        </div>
                      )}
                    </Card>
                  ))}
                </StaggerChildren>
              </div>
            )}
          </>
        )}

        {/* -- Error Message -- */}
        {error && (
          <FadeIn>
            <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          </FadeIn>
        )}
      </PageTransition>
    </Shell>
  );
}
