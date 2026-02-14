/**
 * Campaign management page — create, view, update, and delete ad campaigns.
 *
 * Fetches campaigns from the backend API and displays them in a responsive
 * card grid with status badges, budget information, and action buttons.
 * Includes a create-campaign dialog for adding new campaigns.
 *
 * **For Developers:**
 *   - Fetches from `GET /api/v1/campaigns` on mount.
 *   - Create dialog posts to `POST /api/v1/campaigns`.
 *   - Delete calls `DELETE /api/v1/campaigns/{id}`.
 *   - Status update calls `PATCH /api/v1/campaigns/{id}`.
 *   - Requires at least one ad account to exist before creating campaigns.
 *   - Uses Shell wrapper, motion animations, and the full UI component library.
 *
 * **For Project Managers:**
 *   - Campaigns are the core billable resource (Free: 2, Pro: 25, Enterprise: unlimited).
 *   - Each campaign has an objective, budget, and status lifecycle (draft > active > paused > completed).
 *
 * **For QA Engineers:**
 *   - Test loading skeleton display before data arrives.
 *   - Test empty state when no campaigns exist.
 *   - Test create dialog validation (required fields, budget validation).
 *   - Test status badge colors for each status (draft, active, paused, completed).
 *   - Test delete confirmation and list refresh.
 *   - Test with API server down (error state).
 *
 * **For End Users:**
 *   - Create and manage your advertising campaigns from this page.
 *   - Click "New Campaign" to launch a new campaign with budget and objective settings.
 *   - Use the status toggle to pause or resume campaigns.
 */

"use client";

import * as React from "react";
import {
  Megaphone,
  Plus,
  Trash2,
  Play,
  Pause,
  DollarSign,
  Target,
  Calendar,
  RefreshCw,
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

/** Shape of a campaign returned from the backend. */
interface Campaign {
  id: string;
  user_id: string;
  ad_account_id: string;
  name: string;
  platform: string;
  objective: string;
  budget_daily: number | null;
  budget_lifetime: number | null;
  status: string;
  start_date: string | null;
  end_date: string | null;
  created_at: string;
  updated_at: string;
}

/** Paginated response wrapper from the backend. */
interface PaginatedResponse {
  items: Campaign[];
  total: number;
  offset: number;
  limit: number;
}

/** Shape of an ad account for the create-campaign form. */
interface AdAccount {
  id: string;
  platform: string;
  account_name: string;
  is_connected: boolean;
}

/** Paginated ad accounts response. */
interface AdAccountsResponse {
  items: AdAccount[];
  total: number;
  offset: number;
  limit: number;
}

/* ── Constants ──────────────────────────────────────────────────────── */

/** Campaign status to badge variant mapping. */
const STATUS_VARIANTS: Record<string, "success" | "default" | "secondary" | "destructive"> = {
  active: "success",
  draft: "secondary",
  paused: "default",
  completed: "destructive",
};

/** Campaign objectives for the create form select. */
const OBJECTIVES = [
  { value: "traffic", label: "Traffic" },
  { value: "conversions", label: "Conversions" },
  { value: "awareness", label: "Awareness" },
  { value: "sales", label: "Sales" },
];

/* ── Component ──────────────────────────────────────────────────────── */

/**
 * Campaign management page component.
 *
 * @returns The campaigns page wrapped in the Shell layout with motion animations.
 */
export default function CampaignsPage() {
  const [campaigns, setCampaigns] = React.useState<Campaign[]>([]);
  const [accounts, setAccounts] = React.useState<AdAccount[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [creating, setCreating] = React.useState(false);

  /* ── Create form state ── */
  const [formName, setFormName] = React.useState("");
  const [formObjective, setFormObjective] = React.useState("conversions");
  const [formBudgetDaily, setFormBudgetDaily] = React.useState("");
  const [formBudgetLifetime, setFormBudgetLifetime] = React.useState("");
  const [formAccountId, setFormAccountId] = React.useState("");
  const [formStartDate, setFormStartDate] = React.useState("");
  const [formEndDate, setFormEndDate] = React.useState("");
  const [createError, setCreateError] = React.useState<string | null>(null);

  /**
   * Fetch campaigns and ad accounts from the backend.
   * Called on mount and after create/delete operations.
   */
  const fetchData = React.useCallback(async () => {
    setLoading(true);
    setError(null);

    const [campResult, acctResult] = await Promise.all([
      api.get<PaginatedResponse>("/api/v1/campaigns?limit=100"),
      api.get<AdAccountsResponse>("/api/v1/accounts?limit=100"),
    ]);

    if (campResult.error) {
      setError(campResult.error.message);
    } else if (campResult.data) {
      setCampaigns(campResult.data.items);
    }

    if (acctResult.data) {
      setAccounts(acctResult.data.items.filter((a) => a.is_connected));
    }

    setLoading(false);
  }, []);

  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  /** Set default account when accounts load. */
  React.useEffect(() => {
    if (accounts.length > 0 && !formAccountId) {
      setFormAccountId(accounts[0].id);
    }
  }, [accounts, formAccountId]);

  /**
   * Handle campaign creation form submission.
   * Validates required fields, posts to the API, and refreshes the list.
   */
  async function handleCreate() {
    setCreateError(null);

    if (!formName.trim()) {
      setCreateError("Campaign name is required.");
      return;
    }
    if (!formAccountId) {
      setCreateError("Please connect an ad account first.");
      return;
    }

    setCreating(true);

    const payload: Record<string, unknown> = {
      ad_account_id: formAccountId,
      name: formName.trim(),
      objective: formObjective,
      status: "draft",
    };

    if (formBudgetDaily) payload.budget_daily = parseFloat(formBudgetDaily);
    if (formBudgetLifetime) payload.budget_lifetime = parseFloat(formBudgetLifetime);
    if (formStartDate) payload.start_date = formStartDate;
    if (formEndDate) payload.end_date = formEndDate;

    const { error: apiErr } = await api.post("/api/v1/campaigns", payload);

    if (apiErr) {
      setCreateError(apiErr.message);
    } else {
      setDialogOpen(false);
      resetForm();
      await fetchData();
    }
    setCreating(false);
  }

  /** Reset the create form to its initial state. */
  function resetForm() {
    setFormName("");
    setFormObjective("conversions");
    setFormBudgetDaily("");
    setFormBudgetLifetime("");
    setFormStartDate("");
    setFormEndDate("");
    setCreateError(null);
  }

  /**
   * Toggle a campaign between active and paused status.
   *
   * @param campaign - The campaign to toggle.
   */
  async function toggleStatus(campaign: Campaign) {
    const newStatus = campaign.status === "active" ? "paused" : "active";
    await api.patch(`/api/v1/campaigns/${campaign.id}`, { status: newStatus });
    await fetchData();
  }

  /**
   * Delete a campaign after confirmation.
   *
   * @param id - The UUID of the campaign to delete.
   */
  async function handleDelete(id: string) {
    if (!window.confirm("Are you sure you want to delete this campaign? This cannot be undone.")) {
      return;
    }
    await api.del(`/api/v1/campaigns/${id}`);
    await fetchData();
  }

  /**
   * Format a budget value for display.
   *
   * @param value - The numeric budget value.
   * @returns A formatted currency string, or "---" if null.
   */
  function formatBudget(value: number | null): string {
    if (value === null || value === undefined) return "---";
    return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* ── Header ── */}
        <FadeIn direction="down">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight flex items-center gap-2">
                <Megaphone className="size-6" />
                Campaigns
              </h2>
              <p className="text-muted-foreground mt-1">
                Create and manage your advertising campaigns across platforms.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={fetchData} disabled={loading}>
                <RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} />
                Refresh
              </Button>
              <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
                <DialogTrigger asChild>
                  <Button>
                    <Plus className="size-4" />
                    New Campaign
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Create Campaign</DialogTitle>
                    <DialogDescription>
                      Set up a new advertising campaign. You can adjust settings after creation.
                    </DialogDescription>
                  </DialogHeader>

                  <div className="space-y-4 py-2">
                    {/* Campaign Name */}
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium">Campaign Name *</label>
                      <Input
                        placeholder="e.g. Summer Sale 2026"
                        value={formName}
                        onChange={(e) => setFormName(e.target.value)}
                      />
                    </div>

                    {/* Ad Account */}
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium">Ad Account *</label>
                      {accounts.length === 0 ? (
                        <p className="text-sm text-muted-foreground">
                          No connected ad accounts. Connect one in Settings first.
                        </p>
                      ) : (
                        <select
                          className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          value={formAccountId}
                          onChange={(e) => setFormAccountId(e.target.value)}
                        >
                          {accounts.map((acct) => (
                            <option key={acct.id} value={acct.id}>
                              {acct.account_name} ({acct.platform})
                            </option>
                          ))}
                        </select>
                      )}
                    </div>

                    {/* Objective */}
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium">Objective</label>
                      <select
                        className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        value={formObjective}
                        onChange={(e) => setFormObjective(e.target.value)}
                      >
                        {OBJECTIVES.map((obj) => (
                          <option key={obj.value} value={obj.value}>
                            {obj.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Budget */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium">Daily Budget ($)</label>
                        <Input
                          type="number"
                          min="0"
                          step="0.01"
                          placeholder="50.00"
                          value={formBudgetDaily}
                          onChange={(e) => setFormBudgetDaily(e.target.value)}
                        />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium">Lifetime Budget ($)</label>
                        <Input
                          type="number"
                          min="0"
                          step="0.01"
                          placeholder="5000.00"
                          value={formBudgetLifetime}
                          onChange={(e) => setFormBudgetLifetime(e.target.value)}
                        />
                      </div>
                    </div>

                    {/* Date Range */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium">Start Date</label>
                        <Input
                          type="date"
                          value={formStartDate}
                          onChange={(e) => setFormStartDate(e.target.value)}
                        />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium">End Date</label>
                        <Input
                          type="date"
                          value={formEndDate}
                          onChange={(e) => setFormEndDate(e.target.value)}
                        />
                      </div>
                    </div>

                    {createError && (
                      <p className="text-sm text-destructive">{createError}</p>
                    )}
                  </div>

                  <DialogFooter>
                    <Button variant="outline" onClick={() => setDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button onClick={handleCreate} disabled={creating}>
                      {creating ? "Creating..." : "Create Campaign"}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
          </div>
        </FadeIn>

        {/* ── Campaign Grid ── */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-5 w-40" />
                </CardHeader>
                <CardContent className="space-y-3">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-4 w-20" />
                </CardContent>
                <CardFooter>
                  <Skeleton className="h-8 w-full" />
                </CardFooter>
              </Card>
            ))}
          </div>
        ) : error ? (
          <FadeIn>
            <Card className="border-destructive/50">
              <CardContent className="pt-6">
                <p className="text-destructive text-sm">
                  Failed to load campaigns: {error}
                </p>
                <Button variant="outline" size="sm" className="mt-3" onClick={fetchData}>
                  Retry
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        ) : campaigns.length === 0 ? (
          <FadeIn>
            <Card>
              <CardContent className="pt-6 text-center py-16">
                <Megaphone className="size-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="font-heading text-lg font-semibold">No campaigns yet</h3>
                <p className="text-muted-foreground text-sm mt-1 mb-4">
                  Create your first campaign to start driving results.
                </p>
                <Button onClick={() => setDialogOpen(true)}>
                  <Plus className="size-4" />
                  Create First Campaign
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        ) : (
          <StaggerChildren
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
            staggerDelay={0.06}
          >
            {campaigns.map((campaign) => (
              <Card key={campaign.id} className="group relative overflow-hidden">
                <CardHeader className="flex flex-row items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <CardTitle className="text-base truncate">{campaign.name}</CardTitle>
                    <p className="text-xs text-muted-foreground mt-1 capitalize">
                      {campaign.platform}
                    </p>
                  </div>
                  <Badge variant={STATUS_VARIANTS[campaign.status] || "secondary"}>
                    {campaign.status}
                  </Badge>
                </CardHeader>

                <CardContent className="space-y-3">
                  {/* Objective */}
                  <div className="flex items-center gap-2 text-sm">
                    <Target className="size-3.5 text-muted-foreground shrink-0" />
                    <span className="capitalize">{campaign.objective}</span>
                  </div>

                  {/* Budget */}
                  <div className="flex items-center gap-2 text-sm">
                    <DollarSign className="size-3.5 text-muted-foreground shrink-0" />
                    <span>
                      {campaign.budget_daily !== null
                        ? `${formatBudget(campaign.budget_daily)}/day`
                        : campaign.budget_lifetime !== null
                        ? `${formatBudget(campaign.budget_lifetime)} lifetime`
                        : "No budget set"}
                    </span>
                  </div>

                  {/* Date Range */}
                  {(campaign.start_date || campaign.end_date) && (
                    <div className="flex items-center gap-2 text-sm">
                      <Calendar className="size-3.5 text-muted-foreground shrink-0" />
                      <span>
                        {campaign.start_date
                          ? new Date(campaign.start_date).toLocaleDateString()
                          : "No start"}
                        {" - "}
                        {campaign.end_date
                          ? new Date(campaign.end_date).toLocaleDateString()
                          : "Ongoing"}
                      </span>
                    </div>
                  )}
                </CardContent>

                <CardFooter className="gap-2">
                  {(campaign.status === "active" || campaign.status === "paused") && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => toggleStatus(campaign)}
                    >
                      {campaign.status === "active" ? (
                        <>
                          <Pause className="size-3.5" />
                          Pause
                        </>
                      ) : (
                        <>
                          <Play className="size-3.5" />
                          Resume
                        </>
                      )}
                    </Button>
                  )}
                  {campaign.status === "draft" && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => toggleStatus(campaign)}
                    >
                      <Play className="size-3.5" />
                      Launch
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-muted-foreground hover:text-destructive shrink-0"
                    onClick={() => handleDelete(campaign.id)}
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </StaggerChildren>
        )}

        {/* ── Summary Footer ── */}
        {!loading && campaigns.length > 0 && (
          <FadeIn delay={0.3}>
            <p className="text-xs text-muted-foreground text-center">
              Showing {campaigns.length} campaign{campaigns.length !== 1 ? "s" : ""}
              {" "}&middot;{" "}
              {campaigns.filter((c) => c.status === "active").length} active
              {" "}&middot;{" "}
              {campaigns.filter((c) => c.status === "draft").length} draft
            </p>
          </FadeIn>
        )}
      </PageTransition>
    </Shell>
  );
}
