/**
 * Ad creative management page — create, view, update, and delete ad creatives.
 *
 * Displays ad creatives in a visual card grid with headline previews,
 * status badges, and call-to-action buttons. Includes AI copy generation
 * and a manual create dialog.
 *
 * **For Developers:**
 *   - Fetches from `GET /api/v1/creatives` on mount.
 *   - AI generation posts to `POST /api/v1/creatives/generate-copy`.
 *   - Manual creation posts to `POST /api/v1/creatives`.
 *   - Deletion calls `DELETE /api/v1/creatives/{id}`.
 *   - The creative chain is: account > campaign > ad group > creative.
 *   - Uses Shell wrapper, motion animations, and the full UI component library.
 *
 * **For Project Managers:**
 *   - Creatives are the actual ad content users see (headline + description + CTA).
 *   - AI copy generation is a premium differentiator for AdScale.
 *
 * **For QA Engineers:**
 *   - Test loading skeleton display before data arrives.
 *   - Test empty state when no creatives exist.
 *   - Test AI copy generation returns valid headline, description, CTA.
 *   - Test create dialog validation.
 *   - Test delete and list refresh.
 *   - Test status badges (active, paused, rejected).
 *
 * **For End Users:**
 *   - Create ad creatives manually or let AI generate compelling copy.
 *   - Each creative has a headline, description, destination URL, and CTA.
 *   - Use the AI Generate button to get started quickly.
 */

"use client";

import * as React from "react";
import {
  Image as ImageIcon,
  Plus,
  Trash2,
  Sparkles,
  ExternalLink,
  Copy,
  RefreshCw,
  MousePointerClick,
} from "lucide-react";
import { Shell } from "@/components/shell";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
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
  DialogTrigger,
} from "@/components/ui/dialog";
import { FadeIn, StaggerChildren, PageTransition } from "@/components/motion";
import { api } from "@/lib/api";

/* ── Types ──────────────────────────────────────────────────────────── */

/** Shape of a creative returned from the backend. */
interface Creative {
  id: string;
  ad_group_id: string;
  headline: string;
  description: string;
  image_url: string | null;
  destination_url: string;
  call_to_action: string;
  status: string;
  created_at: string;
  updated_at: string;
}

/** Paginated response wrapper. */
interface PaginatedResponse {
  items: Creative[];
  total: number;
  offset: number;
  limit: number;
}

/** AI-generated copy response. */
interface GeneratedCopy {
  headline: string;
  description: string;
  call_to_action: string;
}

/** Ad group for the create form. */
interface AdGroup {
  id: string;
  campaign_id: string;
  name: string;
}

/** Paginated ad groups response. */
interface AdGroupsResponse {
  items: AdGroup[];
  total: number;
  offset: number;
  limit: number;
}

/* ── Constants ──────────────────────────────────────────────────────── */

/** Creative status to badge variant mapping. */
const STATUS_VARIANTS: Record<string, "success" | "default" | "secondary" | "destructive"> = {
  active: "success",
  paused: "secondary",
  rejected: "destructive",
};

/* ── Component ──────────────────────────────────────────────────────── */

/**
 * Ad creative management page component.
 *
 * @returns The creatives page wrapped in the Shell layout with motion animations.
 */
export default function CreativesPage() {
  const [creatives, setCreatives] = React.useState<Creative[]>([]);
  const [adGroups, setAdGroups] = React.useState<AdGroup[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  /* ── Create dialog state ── */
  const [createOpen, setCreateOpen] = React.useState(false);
  const [creating, setCreating] = React.useState(false);
  const [formHeadline, setFormHeadline] = React.useState("");
  const [formDescription, setFormDescription] = React.useState("");
  const [formDestUrl, setFormDestUrl] = React.useState("");
  const [formCta, setFormCta] = React.useState("Shop Now");
  const [formAdGroupId, setFormAdGroupId] = React.useState("");
  const [createError, setCreateError] = React.useState<string | null>(null);

  /* ── AI generate dialog state ── */
  const [aiOpen, setAiOpen] = React.useState(false);
  const [aiLoading, setAiLoading] = React.useState(false);
  const [aiProductName, setAiProductName] = React.useState("");
  const [aiProductDesc, setAiProductDesc] = React.useState("");
  const [aiAudience, setAiAudience] = React.useState("");
  const [aiTone, setAiTone] = React.useState("");
  const [aiResult, setAiResult] = React.useState<GeneratedCopy | null>(null);
  const [aiError, setAiError] = React.useState<string | null>(null);

  /**
   * Fetch creatives and ad groups from the backend.
   * Called on mount and after create/delete operations.
   */
  const fetchData = React.useCallback(async () => {
    setLoading(true);
    setError(null);

    const [crResult, agResult] = await Promise.all([
      api.get<PaginatedResponse>("/api/v1/creatives?limit=100"),
      api.get<AdGroupsResponse>("/api/v1/ad-groups?limit=100"),
    ]);

    if (crResult.error) {
      setError(crResult.error.message);
    } else if (crResult.data) {
      setCreatives(crResult.data.items);
    }

    if (agResult.data) {
      setAdGroups(agResult.data.items);
    }

    setLoading(false);
  }, []);

  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  /** Set default ad group when ad groups load. */
  React.useEffect(() => {
    if (adGroups.length > 0 && !formAdGroupId) {
      setFormAdGroupId(adGroups[0].id);
    }
  }, [adGroups, formAdGroupId]);

  /** Reset the create form. */
  function resetCreateForm() {
    setFormHeadline("");
    setFormDescription("");
    setFormDestUrl("");
    setFormCta("Shop Now");
    setCreateError(null);
  }

  /** Reset the AI generate form. */
  function resetAiForm() {
    setAiProductName("");
    setAiProductDesc("");
    setAiAudience("");
    setAiTone("");
    setAiResult(null);
    setAiError(null);
  }

  /**
   * Handle manual creative creation.
   * Validates required fields, posts to the API, and refreshes the list.
   */
  async function handleCreate() {
    setCreateError(null);

    if (!formHeadline.trim()) {
      setCreateError("Headline is required.");
      return;
    }
    if (!formDescription.trim()) {
      setCreateError("Description is required.");
      return;
    }
    if (!formDestUrl.trim()) {
      setCreateError("Destination URL is required.");
      return;
    }
    if (!formAdGroupId) {
      setCreateError("Please create an ad group first.");
      return;
    }

    setCreating(true);

    const { error: apiErr } = await api.post("/api/v1/creatives", {
      ad_group_id: formAdGroupId,
      headline: formHeadline.trim(),
      description: formDescription.trim(),
      destination_url: formDestUrl.trim(),
      call_to_action: formCta.trim() || "Shop Now",
    });

    if (apiErr) {
      setCreateError(apiErr.message);
    } else {
      setCreateOpen(false);
      resetCreateForm();
      await fetchData();
    }
    setCreating(false);
  }

  /**
   * Generate AI ad copy from product information.
   * Posts to the generate-copy endpoint and displays the result.
   */
  async function handleAiGenerate() {
    setAiError(null);
    setAiResult(null);

    if (!aiProductName.trim() || !aiProductDesc.trim()) {
      setAiError("Product name and description are required.");
      return;
    }

    setAiLoading(true);

    const payload: Record<string, string> = {
      product_name: aiProductName.trim(),
      product_description: aiProductDesc.trim(),
    };
    if (aiAudience.trim()) payload.target_audience = aiAudience.trim();
    if (aiTone.trim()) payload.tone = aiTone.trim();

    const { data, error: apiErr } = await api.post<GeneratedCopy>(
      "/api/v1/creatives/generate-copy",
      payload
    );

    if (apiErr) {
      setAiError(apiErr.message);
    } else if (data) {
      setAiResult(data);
    }

    setAiLoading(false);
  }

  /**
   * Copy AI-generated copy into the create form and switch dialogs.
   * Pre-fills the create form with the AI result.
   */
  function useAiCopy() {
    if (!aiResult) return;
    setFormHeadline(aiResult.headline);
    setFormDescription(aiResult.description);
    setFormCta(aiResult.call_to_action);
    setAiOpen(false);
    resetAiForm();
    setCreateOpen(true);
  }

  /**
   * Delete a creative after confirmation.
   *
   * @param id - The UUID of the creative to delete.
   */
  async function handleDelete(id: string) {
    if (!window.confirm("Delete this creative? This cannot be undone.")) return;
    await api.del(`/api/v1/creatives/${id}`);
    await fetchData();
  }

  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* ── Header ── */}
        <FadeIn direction="down">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight flex items-center gap-2">
                <ImageIcon className="size-6" />
                Ad Creatives
              </h2>
              <p className="text-muted-foreground mt-1">
                Design compelling ad copy and manage your creative assets.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={fetchData} disabled={loading}>
                <RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} />
                Refresh
              </Button>

              {/* AI Generate Dialog */}
              <Dialog open={aiOpen} onOpenChange={(open) => { setAiOpen(open); if (!open) resetAiForm(); }}>
                <DialogTrigger asChild>
                  <Button variant="outline">
                    <Sparkles className="size-4" />
                    AI Generate
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                      <Sparkles className="size-5" />
                      AI Copy Generator
                    </DialogTitle>
                    <DialogDescription>
                      Describe your product and let AI create compelling ad copy.
                    </DialogDescription>
                  </DialogHeader>

                  <div className="space-y-4 py-2">
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium">Product Name *</label>
                      <Input
                        placeholder="e.g. Wireless Earbuds Pro"
                        value={aiProductName}
                        onChange={(e) => setAiProductName(e.target.value)}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium">Product Description *</label>
                      <textarea
                        className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring min-h-[80px] resize-y"
                        placeholder="Describe the product features, benefits, and what makes it unique..."
                        value={aiProductDesc}
                        onChange={(e) => setAiProductDesc(e.target.value)}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium">Target Audience</label>
                        <Input
                          placeholder="e.g. Young professionals"
                          value={aiAudience}
                          onChange={(e) => setAiAudience(e.target.value)}
                        />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium">Tone</label>
                        <Input
                          placeholder="e.g. Professional, Playful"
                          value={aiTone}
                          onChange={(e) => setAiTone(e.target.value)}
                        />
                      </div>
                    </div>

                    {aiError && <p className="text-sm text-destructive">{aiError}</p>}

                    {/* AI Result Preview */}
                    {aiResult && (
                      <div className="rounded-lg border bg-secondary/30 p-4 space-y-2">
                        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                          Generated Copy
                        </p>
                        <p className="font-semibold text-sm">{aiResult.headline}</p>
                        <p className="text-sm text-muted-foreground">{aiResult.description}</p>
                        <Badge variant="outline">{aiResult.call_to_action}</Badge>
                      </div>
                    )}
                  </div>

                  <DialogFooter>
                    {aiResult ? (
                      <>
                        <Button variant="outline" onClick={handleAiGenerate} disabled={aiLoading}>
                          Regenerate
                        </Button>
                        <Button onClick={useAiCopy}>
                          <Copy className="size-4" />
                          Use This Copy
                        </Button>
                      </>
                    ) : (
                      <>
                        <Button variant="outline" onClick={() => setAiOpen(false)}>
                          Cancel
                        </Button>
                        <Button onClick={handleAiGenerate} disabled={aiLoading}>
                          {aiLoading ? (
                            <>
                              <RefreshCw className="size-4 animate-spin" />
                              Generating...
                            </>
                          ) : (
                            <>
                              <Sparkles className="size-4" />
                              Generate Copy
                            </>
                          )}
                        </Button>
                      </>
                    )}
                  </DialogFooter>
                </DialogContent>
              </Dialog>

              {/* Manual Create Dialog */}
              <Dialog open={createOpen} onOpenChange={(open) => { setCreateOpen(open); if (!open) resetCreateForm(); }}>
                <DialogTrigger asChild>
                  <Button>
                    <Plus className="size-4" />
                    New Creative
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Create Ad Creative</DialogTitle>
                    <DialogDescription>
                      Write ad copy with a headline, description, and call-to-action.
                    </DialogDescription>
                  </DialogHeader>

                  <div className="space-y-4 py-2">
                    {/* Ad Group */}
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium">Ad Group *</label>
                      {adGroups.length === 0 ? (
                        <p className="text-sm text-muted-foreground">
                          No ad groups found. Create a campaign and ad group first.
                        </p>
                      ) : (
                        <select
                          className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          value={formAdGroupId}
                          onChange={(e) => setFormAdGroupId(e.target.value)}
                        >
                          {adGroups.map((ag) => (
                            <option key={ag.id} value={ag.id}>
                              {ag.name}
                            </option>
                          ))}
                        </select>
                      )}
                    </div>

                    {/* Headline */}
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium">Headline *</label>
                      <Input
                        placeholder="e.g. Get 50% Off Premium Earbuds"
                        value={formHeadline}
                        onChange={(e) => setFormHeadline(e.target.value)}
                        maxLength={255}
                      />
                    </div>

                    {/* Description */}
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium">Description *</label>
                      <textarea
                        className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring min-h-[80px] resize-y"
                        placeholder="Describe the offer, benefits, or unique selling point..."
                        value={formDescription}
                        onChange={(e) => setFormDescription(e.target.value)}
                        maxLength={1024}
                      />
                    </div>

                    {/* Destination URL */}
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium">Destination URL *</label>
                      <Input
                        type="url"
                        placeholder="https://yourstore.com/product"
                        value={formDestUrl}
                        onChange={(e) => setFormDestUrl(e.target.value)}
                      />
                    </div>

                    {/* Call to Action */}
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium">Call to Action</label>
                      <Input
                        placeholder="Shop Now"
                        value={formCta}
                        onChange={(e) => setFormCta(e.target.value)}
                        maxLength={50}
                      />
                    </div>

                    {createError && (
                      <p className="text-sm text-destructive">{createError}</p>
                    )}
                  </div>

                  <DialogFooter>
                    <Button variant="outline" onClick={() => setCreateOpen(false)}>
                      Cancel
                    </Button>
                    <Button onClick={handleCreate} disabled={creating}>
                      {creating ? "Creating..." : "Create Creative"}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
          </div>
        </FadeIn>

        {/* ── Creatives Grid ── */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-5 w-48" />
                </CardHeader>
                <CardContent className="space-y-3">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-4 w-24" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : error ? (
          <FadeIn>
            <Card className="border-destructive/50">
              <CardContent className="pt-6">
                <p className="text-destructive text-sm">
                  Failed to load creatives: {error}
                </p>
                <Button variant="outline" size="sm" className="mt-3" onClick={fetchData}>
                  Retry
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        ) : creatives.length === 0 ? (
          <FadeIn>
            <Card>
              <CardContent className="pt-6 text-center py-16">
                <ImageIcon className="size-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="font-heading text-lg font-semibold">No creatives yet</h3>
                <p className="text-muted-foreground text-sm mt-1 mb-4">
                  Start by generating AI copy or creating a creative manually.
                </p>
                <div className="flex items-center justify-center gap-3">
                  <Button variant="outline" onClick={() => setAiOpen(true)}>
                    <Sparkles className="size-4" />
                    AI Generate
                  </Button>
                  <Button onClick={() => setCreateOpen(true)}>
                    <Plus className="size-4" />
                    Create Manually
                  </Button>
                </div>
              </CardContent>
            </Card>
          </FadeIn>
        ) : (
          <StaggerChildren
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
            staggerDelay={0.06}
          >
            {creatives.map((creative) => (
              <Card key={creative.id} className="group relative overflow-hidden">
                {/* Preview banner strip */}
                <div className="h-2 bg-gradient-to-r from-primary/60 to-accent/60" />

                <CardHeader className="flex flex-row items-start justify-between gap-2 pt-4">
                  <div className="min-w-0 flex-1">
                    <CardTitle className="text-base leading-snug">
                      {creative.headline}
                    </CardTitle>
                  </div>
                  <Badge variant={STATUS_VARIANTS[creative.status] || "secondary"}>
                    {creative.status}
                  </Badge>
                </CardHeader>

                <CardContent className="space-y-3">
                  {/* Description preview */}
                  <p className="text-sm text-muted-foreground line-clamp-3">
                    {creative.description}
                  </p>

                  {/* Destination URL */}
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <ExternalLink className="size-3 shrink-0" />
                    <span className="truncate">{creative.destination_url}</span>
                  </div>

                  {/* CTA badge */}
                  <div className="flex items-center gap-1.5">
                    <MousePointerClick className="size-3 text-muted-foreground" />
                    <Badge variant="outline" className="text-xs">
                      {creative.call_to_action}
                    </Badge>
                  </div>
                </CardContent>

                <CardFooter className="gap-2">
                  <p className="text-xs text-muted-foreground flex-1">
                    {new Date(creative.created_at).toLocaleDateString()}
                  </p>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-muted-foreground hover:text-destructive shrink-0"
                    onClick={() => handleDelete(creative.id)}
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </StaggerChildren>
        )}

        {/* ── Summary Footer ── */}
        {!loading && creatives.length > 0 && (
          <FadeIn delay={0.3}>
            <p className="text-xs text-muted-foreground text-center">
              Showing {creatives.length} creative{creatives.length !== 1 ? "s" : ""}
              {" "}&middot;{" "}
              {creatives.filter((c) => c.status === "active").length} active
            </p>
          </FadeIn>
        )}
      </PageTransition>
    </Shell>
  );
}
