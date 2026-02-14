/**
 * Keywords tracking page -- add, monitor, and manage tracked search keywords.
 *
 * Displays all tracked keywords for a selected site with their current rank,
 * previous rank, search volume, and difficulty score. Supports adding new
 * keywords, refreshing rank data, and removing keywords.
 *
 * **For Developers:**
 *   - `GET /api/v1/sites` -- fetch sites for the site selector dropdown.
 *   - `GET /api/v1/keywords?site_id=...` -- list keywords (paginated).
 *   - `POST /api/v1/keywords` -- add keyword `{ site_id, keyword }`.
 *   - `DELETE /api/v1/keywords/:id?site_id=...` -- remove a keyword.
 *   - `POST /api/v1/keywords/refresh?site_id=...` -- refresh rank data.
 *   - Keywords are scoped to a site. The user must select a site first.
 *
 * **For Project Managers:**
 *   - Keyword tracking is the secondary usage metric tied to plan limits.
 *   - The refresh button triggers a rank update (mock in development).
 *   - Rank trend arrows (up/down) help users see progress at a glance.
 *
 * **For QA Engineers:**
 *   - Verify loading skeletons during data fetch.
 *   - Test adding a keyword and confirming it appears in the list.
 *   - Test deleting a keyword and confirming it disappears.
 *   - Test refresh button updates rank data.
 *   - Test with no sites -- should show a "create a site first" message.
 *   - Test duplicate keyword rejection shows an error.
 *
 * **For End Users:**
 *   - Select a site from the dropdown to view its tracked keywords.
 *   - Add keywords to monitor their search engine rankings.
 *   - Use the refresh button to get updated ranking data.
 */

"use client";

import * as React from "react";
import {
  Search,
  Plus,
  Trash2,
  RefreshCw,
  Loader2,
  TrendingUp,
  TrendingDown,
  Minus,
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
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
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

/** Shape of a tracked keyword record. */
interface Keyword {
  id: string;
  site_id: string;
  keyword: string;
  current_rank: number | null;
  previous_rank: number | null;
  search_volume: number | null;
  difficulty: number | null;
  tracked_since: string;
  last_checked: string | null;
}

/** Paginated response envelope for keywords. */
interface PaginatedKeywords {
  items: Keyword[];
  total: number;
  page: number;
  per_page: number;
}

/**
 * Keywords tracking page component.
 *
 * @returns The keywords page wrapped in the Shell layout.
 */
export default function KeywordsPage() {
  /* Site selection */
  const [sites, setSites] = React.useState<Site[]>([]);
  const [selectedSiteId, setSelectedSiteId] = React.useState<string | null>(null);
  const [sitesLoading, setSitesLoading] = React.useState(true);

  /* Keywords list */
  const [keywords, setKeywords] = React.useState<Keyword[]>([]);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  /* Add keyword dialog state */
  const [addOpen, setAddOpen] = React.useState(false);
  const [newKeyword, setNewKeyword] = React.useState("");
  const [adding, setAdding] = React.useState(false);

  /* Refresh state */
  const [refreshing, setRefreshing] = React.useState(false);

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
   * Fetch keywords whenever the selected site changes.
   */
  React.useEffect(() => {
    if (selectedSiteId) {
      fetchKeywords(selectedSiteId);
    }
  }, [selectedSiteId]);

  /**
   * Fetch the list of keywords for a site.
   *
   * @param siteId - The UUID of the site to fetch keywords for.
   */
  async function fetchKeywords(siteId: string) {
    setLoading(true);
    setError(null);
    const { data, error: apiError } = await api.get<PaginatedKeywords>(
      `/api/v1/keywords?site_id=${siteId}&per_page=200`
    );
    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setKeywords(data.items);
      setTotal(data.total);
    }
    setLoading(false);
  }

  /**
   * Add a new keyword to track for the selected site.
   */
  async function handleAddKeyword() {
    if (!newKeyword.trim() || !selectedSiteId) return;

    setAdding(true);
    setError(null);

    const { error: apiError } = await api.post<Keyword>("/api/v1/keywords", {
      site_id: selectedSiteId,
      keyword: newKeyword.trim(),
    });
    setAdding(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    setAddOpen(false);
    setNewKeyword("");
    fetchKeywords(selectedSiteId);
  }

  /**
   * Delete a keyword from tracking.
   *
   * @param keywordId - The UUID of the keyword to remove.
   */
  async function handleDeleteKeyword(keywordId: string) {
    if (!selectedSiteId) return;

    const { error: apiError } = await api.del(
      `/api/v1/keywords/${keywordId}?site_id=${selectedSiteId}`
    );

    if (apiError) {
      setError(apiError.message);
      return;
    }

    fetchKeywords(selectedSiteId);
  }

  /**
   * Refresh keyword rankings for the selected site.
   */
  async function handleRefresh() {
    if (!selectedSiteId) return;

    setRefreshing(true);
    const { error: apiError } = await api.post<{ updated: number }>(
      `/api/v1/keywords/refresh?site_id=${selectedSiteId}`
    );
    setRefreshing(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    fetchKeywords(selectedSiteId);
  }

  /**
   * Render a rank trend indicator based on current vs previous rank.
   *
   * @param current - Current rank position.
   * @param previous - Previous rank position.
   * @returns A JSX element showing an up/down/stable trend indicator.
   */
  function renderTrend(current: number | null, previous: number | null) {
    if (current === null || previous === null) {
      return <Minus className="size-4 text-muted-foreground" />;
    }
    if (current < previous) {
      /* Lower rank number = higher position = improvement */
      return (
        <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 text-xs font-medium">
          <TrendingUp className="size-3.5" />
          +{previous - current}
        </span>
      );
    }
    if (current > previous) {
      return (
        <span className="flex items-center gap-1 text-red-600 dark:text-red-400 text-xs font-medium">
          <TrendingDown className="size-3.5" />
          -{current - previous}
        </span>
      );
    }
    return (
      <span className="flex items-center gap-1 text-muted-foreground text-xs">
        <Minus className="size-3.5" />
        Stable
      </span>
    );
  }

  /**
   * Render the difficulty score as a colored badge.
   *
   * @param difficulty - The difficulty score (0-100) or null.
   * @returns A Badge element with color-coded difficulty level.
   */
  function renderDifficulty(difficulty: number | null) {
    if (difficulty === null) return <span className="text-muted-foreground text-xs">--</span>;
    let variant: "success" | "secondary" | "destructive" = "success";
    if (difficulty >= 60) variant = "destructive";
    else if (difficulty >= 30) variant = "secondary";
    return (
      <Badge variant={variant} className="text-xs tabular-nums">
        {difficulty.toFixed(0)}
      </Badge>
    );
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
                Keywords
              </h2>
              <p className="text-muted-foreground mt-1">
                Track search engine rankings for your target keywords.
              </p>
            </div>
            <div className="flex items-center gap-2">
              {selectedSiteId && keywords.length > 0 && (
                <Button
                  variant="outline"
                  onClick={handleRefresh}
                  disabled={refreshing}
                >
                  {refreshing ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <RefreshCw className="size-4" />
                  )}
                  Refresh Ranks
                </Button>
              )}
              {selectedSiteId && (
                <Button onClick={() => setAddOpen(true)}>
                  <Plus className="size-4" />
                  Add Keyword
                </Button>
              )}
            </div>
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
                  <Search className="size-6 text-muted-foreground" />
                </div>
                <h3 className="font-heading font-semibold text-lg">
                  No sites registered
                </h3>
                <p className="text-muted-foreground text-sm mt-1 max-w-sm mx-auto">
                  Add a site first before you can track keyword rankings.
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
              <label htmlFor="site-select" className="text-sm font-medium whitespace-nowrap">
                Site:
              </label>
              <select
                id="site-select"
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
              {selectedSite && (
                <Badge variant={selectedSite.is_verified ? "success" : "secondary"} className="text-xs">
                  {selectedSite.is_verified ? "Verified" : "Unverified"}
                </Badge>
              )}
            </div>
          </FadeIn>
        )}

        {/* -- KPI Summary -- */}
        {selectedSiteId && !loading && keywords.length > 0 && (
          <FadeIn delay={0.1}>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Card className="py-4">
                <CardContent className="text-center">
                  <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">
                    Total Keywords
                  </p>
                  <AnimatedCounter
                    value={total}
                    className="text-2xl font-bold font-heading"
                  />
                </CardContent>
              </Card>
              <Card className="py-4">
                <CardContent className="text-center">
                  <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">
                    Ranked
                  </p>
                  <AnimatedCounter
                    value={keywords.filter((k) => k.current_rank !== null).length}
                    className="text-2xl font-bold font-heading"
                  />
                </CardContent>
              </Card>
              <Card className="py-4">
                <CardContent className="text-center">
                  <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">
                    Avg. Rank
                  </p>
                  <span className="text-2xl font-bold font-heading">
                    {(() => {
                      const ranked = keywords.filter((k) => k.current_rank !== null);
                      if (ranked.length === 0) return "--";
                      const avg =
                        ranked.reduce((sum, k) => sum + (k.current_rank || 0), 0) /
                        ranked.length;
                      return avg.toFixed(1);
                    })()}
                  </span>
                </CardContent>
              </Card>
            </div>
          </FadeIn>
        )}

        {/* -- Keywords Table -- */}
        {selectedSiteId && (
          <>
            {loading ? (
              <Card>
                <CardContent className="pt-6 space-y-3">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="flex items-center gap-4">
                      <Skeleton className="h-4 w-48 flex-1" />
                      <Skeleton className="h-4 w-16" />
                      <Skeleton className="h-4 w-16" />
                      <Skeleton className="h-4 w-16" />
                      <Skeleton className="h-8 w-8" />
                    </div>
                  ))}
                </CardContent>
              </Card>
            ) : keywords.length === 0 ? (
              <FadeIn>
                <Card>
                  <CardContent className="pt-12 pb-12 text-center">
                    <div className="mx-auto size-12 rounded-full bg-muted flex items-center justify-center mb-4">
                      <Search className="size-6 text-muted-foreground" />
                    </div>
                    <h3 className="font-heading font-semibold text-lg">
                      No keywords tracked
                    </h3>
                    <p className="text-muted-foreground text-sm mt-1 max-w-sm mx-auto">
                      Add keywords to start monitoring their search engine rankings.
                    </p>
                    <Button className="mt-4" onClick={() => setAddOpen(true)}>
                      <Plus className="size-4" />
                      Track your first keyword
                    </Button>
                  </CardContent>
                </Card>
              </FadeIn>
            ) : (
              <FadeIn delay={0.2}>
                <Card>
                  <CardContent className="pt-4">
                    {/* Table Header */}
                    <div className="grid grid-cols-12 gap-3 px-2 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider border-b mb-1">
                      <div className="col-span-5">Keyword</div>
                      <div className="col-span-1 text-center">Rank</div>
                      <div className="col-span-2 text-center">Trend</div>
                      <div className="col-span-1 text-center">Volume</div>
                      <div className="col-span-2 text-center">Difficulty</div>
                      <div className="col-span-1" />
                    </div>

                    {/* Table Rows */}
                    <StaggerChildren className="divide-y" staggerDelay={0.03}>
                      {keywords.map((kw) => (
                        <div
                          key={kw.id}
                          className="grid grid-cols-12 gap-3 px-2 py-3 items-center hover:bg-secondary/30 rounded-md transition-colors"
                        >
                          <div className="col-span-5">
                            <p className="text-sm font-medium truncate">
                              {kw.keyword}
                            </p>
                            {kw.last_checked && (
                              <p className="text-xs text-muted-foreground mt-0.5">
                                Checked{" "}
                                {new Date(kw.last_checked).toLocaleDateString()}
                              </p>
                            )}
                          </div>
                          <div className="col-span-1 text-center">
                            <span className="text-sm font-bold tabular-nums">
                              {kw.current_rank !== null
                                ? `#${kw.current_rank}`
                                : "--"}
                            </span>
                          </div>
                          <div className="col-span-2 flex justify-center">
                            {renderTrend(kw.current_rank, kw.previous_rank)}
                          </div>
                          <div className="col-span-1 text-center">
                            <span className="text-xs tabular-nums text-muted-foreground">
                              {kw.search_volume !== null
                                ? kw.search_volume.toLocaleString()
                                : "--"}
                            </span>
                          </div>
                          <div className="col-span-2 flex justify-center">
                            {renderDifficulty(kw.difficulty)}
                          </div>
                          <div className="col-span-1 flex justify-end">
                            <Button
                              variant="ghost"
                              size="icon"
                              className="size-8 text-muted-foreground hover:text-destructive"
                              onClick={() => handleDeleteKeyword(kw.id)}
                            >
                              <Trash2 className="size-3.5" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </StaggerChildren>
                  </CardContent>
                </Card>
              </FadeIn>
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

        {/* -- Add Keyword Dialog -- */}
        <Dialog open={addOpen} onOpenChange={setAddOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Keyword</DialogTitle>
              <DialogDescription>
                Add a search keyword to track its ranking position for{" "}
                <strong>{selectedSite?.domain || "the selected site"}</strong>.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <label htmlFor="keyword-input" className="text-sm font-medium">
                  Keyword
                </label>
                <Input
                  id="keyword-input"
                  placeholder='e.g. "best seo tools 2026"'
                  value={newKeyword}
                  onChange={(e) => setNewKeyword(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleAddKeyword();
                  }}
                />
                <p className="text-xs text-muted-foreground">
                  Enter the exact search phrase you want to track.
                </p>
              </div>
            </div>

            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setAddOpen(false)}
                disabled={adding}
              >
                Cancel
              </Button>
              <Button onClick={handleAddKeyword} disabled={adding}>
                {adding && <Loader2 className="size-4 animate-spin" />}
                {adding ? "Adding..." : "Add Keyword"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageTransition>
    </Shell>
  );
}
