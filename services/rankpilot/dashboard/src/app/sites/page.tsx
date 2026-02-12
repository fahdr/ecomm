/**
 * Sites management page -- add, view, verify, and remove tracked domains.
 *
 * Lists all sites (domains) registered by the authenticated user. Provides
 * a dialog to add new sites, inline verification, and deletion with confirmation.
 *
 * **For Developers:**
 *   - `GET /api/v1/sites` -- list sites (paginated).
 *   - `POST /api/v1/sites` -- create site `{ domain, sitemap_url? }`.
 *   - `POST /api/v1/sites/:id/verify` -- trigger domain verification.
 *   - `DELETE /api/v1/sites/:id` -- remove a site and all child data.
 *   - Uses Shell wrapper, Dialog for create flow, and StaggerChildren for list animation.
 *
 * **For Project Managers:**
 *   - Sites are the top-level resource. Users must register a site before
 *     they can use keywords, audits, blog posts, or schema features.
 *   - The verification step is a mock for now but establishes the UX pattern.
 *
 * **For QA Engineers:**
 *   - Verify loading skeletons display before data arrives.
 *   - Test creating a site with a valid domain, then verify it appears in the list.
 *   - Test verification button changes badge from "pending" to "verified".
 *   - Test delete confirmation dialog and that the site disappears after deletion.
 *   - Test empty state when no sites exist.
 *   - Test with API server down -- should show error, not crash.
 *
 * **For End Users:**
 *   - Register your domains to start tracking SEO metrics.
 *   - Verify domain ownership to unlock full features.
 *   - Remove sites you no longer want to track.
 */

"use client";

import * as React from "react";
import {
  Globe,
  Plus,
  ShieldCheck,
  Trash2,
  Loader2,
  ExternalLink,
  MapPin,
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
} from "@/components/motion";
import { api } from "@/lib/api";

/** Shape of a site record as returned by the list endpoint. */
interface Site {
  id: string;
  user_id: string;
  domain: string;
  sitemap_url: string | null;
  verification_method: string | null;
  is_verified: boolean;
  last_crawled: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

/** Paginated response envelope for sites. */
interface PaginatedSites {
  items: Site[];
  total: number;
  page: number;
  per_page: number;
}

/**
 * Sites management page component.
 *
 * @returns The sites page wrapped in the Shell layout.
 */
export default function SitesPage() {
  const [sites, setSites] = React.useState<Site[]>([]);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  /* Add site dialog state */
  const [addOpen, setAddOpen] = React.useState(false);
  const [newDomain, setNewDomain] = React.useState("");
  const [newSitemap, setNewSitemap] = React.useState("");
  const [creating, setCreating] = React.useState(false);

  /* Delete confirmation state */
  const [deleteTarget, setDeleteTarget] = React.useState<Site | null>(null);
  const [deleting, setDeleting] = React.useState(false);

  /* Verification in-progress tracker (site ID) */
  const [verifyingId, setVerifyingId] = React.useState<string | null>(null);

  /**
   * Fetch all sites on mount.
   */
  React.useEffect(() => {
    fetchSites();
  }, []);

  /**
   * Fetch the list of sites from the backend.
   */
  async function fetchSites() {
    setLoading(true);
    setError(null);
    const { data, error: apiError } = await api.get<PaginatedSites>(
      "/api/v1/sites?per_page=100"
    );
    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setSites(data.items);
      setTotal(data.total);
    }
    setLoading(false);
  }

  /**
   * Create a new site with the provided domain and optional sitemap URL.
   */
  async function handleAddSite() {
    if (!newDomain.trim()) {
      setError("Please enter a domain name.");
      return;
    }

    setCreating(true);
    setError(null);

    const payload: Record<string, string> = { domain: newDomain.trim() };
    if (newSitemap.trim()) {
      payload.sitemap_url = newSitemap.trim();
    }

    const { error: apiError } = await api.post<Site>("/api/v1/sites", payload);
    setCreating(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    setAddOpen(false);
    setNewDomain("");
    setNewSitemap("");
    fetchSites();
  }

  /**
   * Verify domain ownership for a site (mock -- always succeeds).
   *
   * @param siteId - The UUID of the site to verify.
   */
  async function handleVerify(siteId: string) {
    setVerifyingId(siteId);
    const { error: apiError } = await api.post<Site>(
      `/api/v1/sites/${siteId}/verify`
    );
    setVerifyingId(null);

    if (apiError) {
      setError(apiError.message);
      return;
    }
    fetchSites();
  }

  /**
   * Delete a site permanently.
   *
   * @param siteId - The UUID of the site to delete.
   */
  async function handleDelete(siteId: string) {
    setDeleting(true);
    const { error: apiError } = await api.del(`/api/v1/sites/${siteId}`);
    setDeleting(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    setDeleteTarget(null);
    fetchSites();
  }

  /**
   * Format a date string for display.
   *
   * @param dateStr - ISO date string.
   * @returns Formatted date or "Never" for null.
   */
  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "Never";
    return new Date(dateStr).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* -- Page Header -- */}
        <FadeIn direction="down">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight">
                Sites
              </h2>
              <p className="text-muted-foreground mt-1">
                Manage the domains you are tracking for SEO.
              </p>
            </div>
            <Button onClick={() => setAddOpen(true)}>
              <Plus className="size-4" />
              Add Site
            </Button>
          </div>
        </FadeIn>

        {/* -- Sites List -- */}
        {loading ? (
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <Card key={i}>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-4">
                    <Skeleton className="size-10 rounded-lg" />
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
        ) : sites.length === 0 ? (
          <FadeIn>
            <Card>
              <CardContent className="pt-12 pb-12 text-center">
                <div className="mx-auto size-12 rounded-full bg-muted flex items-center justify-center mb-4">
                  <Globe className="size-6 text-muted-foreground" />
                </div>
                <h3 className="font-heading font-semibold text-lg">
                  No sites tracked yet
                </h3>
                <p className="text-muted-foreground text-sm mt-1 max-w-sm mx-auto">
                  Add your first website domain to start monitoring SEO metrics,
                  running audits, and tracking keyword rankings.
                </p>
                <Button className="mt-4" onClick={() => setAddOpen(true)}>
                  <Plus className="size-4" />
                  Add your first site
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        ) : (
          <StaggerChildren className="space-y-3" staggerDelay={0.06}>
            {sites.map((site) => (
              <Card key={site.id} className="py-4">
                <CardContent className="flex items-center gap-4">
                  {/* Site Icon */}
                  <div className="size-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                    <Globe className="size-5 text-primary" />
                  </div>

                  {/* Site Details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium truncate">{site.domain}</p>
                      {site.is_verified ? (
                        <Badge variant="success" className="text-xs">
                          <ShieldCheck className="size-3 mr-1" />
                          Verified
                        </Badge>
                      ) : (
                        <Badge variant="secondary" className="text-xs">
                          Pending
                        </Badge>
                      )}
                      <Badge
                        variant={
                          site.status === "active"
                            ? "success"
                            : site.status === "error"
                            ? "destructive"
                            : "outline"
                        }
                        className="text-xs"
                      >
                        {site.status}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
                      <span>Added {formatDate(site.created_at)}</span>
                      {site.sitemap_url && (
                        <span className="flex items-center gap-1">
                          <MapPin className="size-3" />
                          Sitemap configured
                        </span>
                      )}
                      {site.last_crawled && (
                        <span>Last crawled {formatDate(site.last_crawled)}</span>
                      )}
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex items-center gap-2 shrink-0">
                    {!site.is_verified && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleVerify(site.id)}
                        disabled={verifyingId === site.id}
                      >
                        {verifyingId === site.id ? (
                          <Loader2 className="size-4 animate-spin" />
                        ) : (
                          <ShieldCheck className="size-4" />
                        )}
                        <span className="hidden sm:inline">Verify</span>
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-muted-foreground hover:text-destructive"
                      onClick={() => setDeleteTarget(site)}
                    >
                      <Trash2 className="size-4" />
                      <span className="hidden sm:inline">Remove</span>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </StaggerChildren>
        )}

        {/* -- Summary -- */}
        {!loading && sites.length > 0 && (
          <FadeIn delay={0.3}>
            <p className="text-xs text-muted-foreground text-center">
              Showing {sites.length} of {total} sites
            </p>
          </FadeIn>
        )}

        {/* -- Error Message -- */}
        {error && (
          <FadeIn>
            <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          </FadeIn>
        )}

        {/* -- Add Site Dialog -- */}
        <Dialog open={addOpen} onOpenChange={setAddOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Site</DialogTitle>
              <DialogDescription>
                Register a new domain to start tracking its SEO performance.
                You can verify domain ownership after creation.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2">
              {/* Domain */}
              <div className="space-y-2">
                <label htmlFor="site-domain" className="text-sm font-medium">
                  Domain
                </label>
                <Input
                  id="site-domain"
                  placeholder="e.g. mystore.com"
                  value={newDomain}
                  onChange={(e) => setNewDomain(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Enter the root domain without protocol (no https://).
                </p>
              </div>

              {/* Sitemap URL (optional) */}
              <div className="space-y-2">
                <label htmlFor="site-sitemap" className="text-sm font-medium">
                  Sitemap URL{" "}
                  <span className="text-muted-foreground font-normal">
                    (optional)
                  </span>
                </label>
                <Input
                  id="site-sitemap"
                  placeholder="e.g. https://mystore.com/sitemap.xml"
                  value={newSitemap}
                  onChange={(e) => setNewSitemap(e.target.value)}
                />
              </div>
            </div>

            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setAddOpen(false)}
                disabled={creating}
              >
                Cancel
              </Button>
              <Button onClick={handleAddSite} disabled={creating}>
                {creating && <Loader2 className="size-4 animate-spin" />}
                {creating ? "Adding..." : "Add Site"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* -- Delete Confirmation Dialog -- */}
        <Dialog
          open={deleteTarget !== null}
          onOpenChange={(open) => {
            if (!open) setDeleteTarget(null);
          }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Remove Site</DialogTitle>
              <DialogDescription>
                Are you sure you want to remove{" "}
                <strong>{deleteTarget?.domain}</strong>? This will permanently
                delete all associated blog posts, keyword tracking data, audits,
                and schema configurations.
              </DialogDescription>
            </DialogHeader>

            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setDeleteTarget(null)}
                disabled={deleting}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={() =>
                  deleteTarget && handleDelete(deleteTarget.id)
                }
                disabled={deleting}
              >
                {deleting && <Loader2 className="size-4 animate-spin" />}
                {deleting ? "Removing..." : "Remove Site"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageTransition>
    </Shell>
  );
}
