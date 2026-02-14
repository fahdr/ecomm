/**
 * Campaigns page — create, manage, send, and track email campaigns.
 *
 * Displays a filterable, paginated list of campaigns with status badges,
 * send counts, and action buttons. Includes dialogs for creating campaigns,
 * editing draft campaigns, confirming sends, and viewing post-send analytics.
 *
 * **For Developers:**
 *   - `GET /api/v1/campaigns?page=&page_size=&status=` — paginated campaign list.
 *   - `POST /api/v1/campaigns` — create a campaign (draft or scheduled).
 *   - `PATCH /api/v1/campaigns/:id` — update a draft campaign.
 *   - `DELETE /api/v1/campaigns/:id` — delete a draft campaign (204).
 *   - `POST /api/v1/campaigns/:id/send` — send a campaign (mock, creates events).
 *   - `GET /api/v1/campaigns/:id/analytics` — per-campaign analytics.
 *   - Status lifecycle: draft -> sent, draft -> scheduled -> sent.
 *   - Sent campaigns cannot be updated or deleted.
 *
 * **For Project Managers:**
 *   - Campaigns are the primary revenue driver for email marketing.
 *   - The send flow is intentionally two-step (create then send) to prevent
 *     accidental blasts. A confirmation dialog adds an extra safety layer.
 *   - Post-send analytics provide immediate feedback on performance.
 *
 * **For QA Engineers:**
 *   - Test with 0 campaigns (empty state), draft, scheduled, and sent campaigns.
 *   - Verify status filter shows only matching campaigns.
 *   - Verify draft campaigns show Edit/Delete/Send buttons; sent campaigns show only Analytics.
 *   - Test the send confirmation dialog — cancellation should not send.
 *   - Verify sent campaigns cannot be updated or deleted (buttons hidden).
 *   - Test with API errors to verify error states render correctly.
 *
 * **For End Users:**
 *   - Create email campaigns and send them to your subscribers.
 *   - Draft campaigns can be edited before sending.
 *   - After sending, view analytics to track opens, clicks, and bounces.
 */

"use client";

import * as React from "react";
import {
  Megaphone,
  Plus,
  Send,
  Trash2,
  Pencil,
  Loader2,
  BarChart3,
  Clock,
  CheckCircle2,
  FileEdit,
  ChevronLeft,
  ChevronRight,
  CalendarClock,
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
  AnimatedCounter,
  PageTransition,
} from "@/components/motion";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

/** Shape of a campaign as returned by the API. */
interface Campaign {
  id: string;
  name: string;
  subject: string;
  status: string;
  scheduled_at: string | null;
  sent_at: string | null;
  total_recipients: number;
  sent_count: number;
  open_count: number;
  click_count: number;
  bounce_count: number;
  created_at: string;
  updated_at: string;
}

/** Shape of a paginated API response. */
interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

/** Shape of per-campaign analytics. */
interface CampaignAnalytics {
  campaign_id: string;
  campaign_name: string;
  total_sent: number;
  total_opened: number;
  total_clicked: number;
  total_bounced: number;
  open_rate: number;
  click_rate: number;
  bounce_rate: number;
}

/** Status filter options for the campaign list. */
const STATUS_FILTERS = [
  { label: "All", value: "" },
  { label: "Draft", value: "draft" },
  { label: "Scheduled", value: "scheduled" },
  { label: "Sent", value: "sent" },
];

/**
 * Map a campaign status string to a Badge variant.
 *
 * @param status - The campaign status string.
 * @returns The appropriate badge variant.
 */
function statusVariant(
  status: string
): "default" | "secondary" | "success" | "destructive" | "outline" {
  switch (status) {
    case "sent":
      return "success";
    case "scheduled":
      return "default";
    case "draft":
      return "secondary";
    default:
      return "outline";
  }
}

/**
 * Get the icon component for a campaign status.
 *
 * @param status - The campaign status string.
 * @returns A React element for the status icon.
 */
function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case "sent":
      return <CheckCircle2 className="size-3.5" />;
    case "scheduled":
      return <CalendarClock className="size-3.5" />;
    case "draft":
      return <FileEdit className="size-3.5" />;
    default:
      return <Clock className="size-3.5" />;
  }
}

/**
 * Campaigns page component.
 *
 * @returns The campaigns management page wrapped in the Shell layout.
 */
export default function CampaignsPage() {
  /* ── List state ── */
  const [campaigns, setCampaigns] = React.useState<Campaign[]>([]);
  const [totalCampaigns, setTotalCampaigns] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [pageSize] = React.useState(20);
  const [statusFilter, setStatusFilter] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  /* ── Create dialog state ── */
  const [createOpen, setCreateOpen] = React.useState(false);
  const [newName, setNewName] = React.useState("");
  const [newSubject, setNewSubject] = React.useState("");
  const [newScheduledAt, setNewScheduledAt] = React.useState("");
  const [creating, setCreating] = React.useState(false);

  /* ── Edit dialog state ── */
  const [editTarget, setEditTarget] = React.useState<Campaign | null>(null);
  const [editName, setEditName] = React.useState("");
  const [editSubject, setEditSubject] = React.useState("");
  const [saving, setSaving] = React.useState(false);

  /* ── Send confirmation state ── */
  const [sendTarget, setSendTarget] = React.useState<Campaign | null>(null);
  const [sending, setSending] = React.useState(false);

  /* ── Delete confirmation state ── */
  const [deleteTarget, setDeleteTarget] = React.useState<Campaign | null>(null);
  const [deleting, setDeleting] = React.useState(false);

  /* ── Analytics dialog state ── */
  const [analyticsTarget, setAnalyticsTarget] =
    React.useState<CampaignAnalytics | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = React.useState(false);

  /**
   * Fetch campaigns from the API with current pagination and status filter.
   */
  async function fetchCampaigns() {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (statusFilter) params.set("status", statusFilter);

    const { data, error: apiError } = await api.get<
      PaginatedResponse<Campaign>
    >(`/api/v1/campaigns?${params.toString()}`);
    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setCampaigns(data.items);
      setTotalCampaigns(data.total);
    }
    setLoading(false);
  }

  /** Fetch on mount and when page/filter changes. */
  React.useEffect(() => {
    fetchCampaigns();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, statusFilter]);

  /**
   * Create a new campaign via the API.
   */
  async function handleCreate() {
    if (!newName.trim() || !newSubject.trim()) {
      setError("Name and subject are required.");
      return;
    }
    setCreating(true);
    setError(null);

    const body: Record<string, unknown> = {
      name: newName.trim(),
      subject: newSubject.trim(),
    };
    if (newScheduledAt) body.scheduled_at = newScheduledAt;

    const { error: apiError } = await api.post("/api/v1/campaigns", body);
    setCreating(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    setCreateOpen(false);
    setNewName("");
    setNewSubject("");
    setNewScheduledAt("");
    fetchCampaigns();
  }

  /**
   * Open the edit dialog pre-filled with the selected campaign.
   *
   * @param campaign - The campaign to edit.
   */
  function openEditDialog(campaign: Campaign) {
    setEditTarget(campaign);
    setEditName(campaign.name);
    setEditSubject(campaign.subject);
  }

  /**
   * Save edits to the selected campaign via PATCH.
   */
  async function handleSaveEdit() {
    if (!editTarget) return;
    setSaving(true);
    setError(null);

    const { error: apiError } = await api.patch(
      `/api/v1/campaigns/${editTarget.id}`,
      {
        name: editName.trim() || undefined,
        subject: editSubject.trim() || undefined,
      }
    );
    setSaving(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    setEditTarget(null);
    fetchCampaigns();
  }

  /**
   * Send a campaign after user confirmation.
   *
   * @param id - The campaign UUID.
   */
  async function handleSend(id: string) {
    setSending(true);
    setError(null);

    const { error: apiError } = await api.post(
      `/api/v1/campaigns/${id}/send`
    );
    setSending(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    setSendTarget(null);
    fetchCampaigns();
  }

  /**
   * Delete a campaign after user confirmation.
   *
   * @param id - The campaign UUID.
   */
  async function handleDelete(id: string) {
    setDeleting(true);
    const { error: apiError } = await api.del(`/api/v1/campaigns/${id}`);
    setDeleting(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    setDeleteTarget(null);
    fetchCampaigns();
  }

  /**
   * Fetch and display analytics for a campaign.
   *
   * @param campaignId - The campaign UUID.
   */
  async function handleViewAnalytics(campaignId: string) {
    setAnalyticsLoading(true);
    const { data, error: apiError } = await api.get<CampaignAnalytics>(
      `/api/v1/campaigns/${campaignId}/analytics`
    );
    setAnalyticsLoading(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    if (data) setAnalyticsTarget(data);
  }

  /** Calculate pagination values. */
  const totalPages = Math.max(1, Math.ceil(totalCampaigns / pageSize));

  /** Count campaigns by status for KPI cards. */
  const draftCount = campaigns.filter((c) => c.status === "draft").length;
  const sentCount = campaigns.filter((c) => c.status === "sent").length;

  /**
   * Format a date string for display.
   *
   * @param dateStr - ISO date string or null.
   * @returns Formatted date or "--".
   */
  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "--";
    return new Date(dateStr).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* ── Page Header ── */}
        <FadeIn direction="down">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight">
                Campaigns
              </h2>
              <p className="text-muted-foreground mt-1">
                Create and manage email campaigns to engage your subscribers.
              </p>
            </div>
            <Button onClick={() => setCreateOpen(true)}>
              <Plus className="size-4" />
              New Campaign
            </Button>
          </div>
        </FadeIn>

        {/* ── KPI Summary Cards ── */}
        <StaggerChildren
          className="grid grid-cols-1 md:grid-cols-3 gap-4"
          staggerDelay={0.08}
        >
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Campaigns
              </CardTitle>
              <Megaphone className="size-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <AnimatedCounter
                value={totalCampaigns}
                className="text-3xl font-bold font-heading"
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Drafts
              </CardTitle>
              <FileEdit className="size-4 text-amber-500" />
            </CardHeader>
            <CardContent>
              <AnimatedCounter
                value={draftCount}
                className="text-3xl font-bold font-heading text-amber-600 dark:text-amber-400"
              />
              <p className="text-xs text-muted-foreground mt-1">
                ready to send
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Sent
              </CardTitle>
              <CheckCircle2 className="size-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              <AnimatedCounter
                value={sentCount}
                className="text-3xl font-bold font-heading text-emerald-600 dark:text-emerald-400"
              />
              <p className="text-xs text-muted-foreground mt-1">
                on current page
              </p>
            </CardContent>
          </Card>
        </StaggerChildren>

        {/* ── Status Filter Tabs ── */}
        <FadeIn delay={0.15}>
          <div className="flex items-center gap-2">
            {STATUS_FILTERS.map((filter) => (
              <Button
                key={filter.value}
                variant={statusFilter === filter.value ? "default" : "outline"}
                size="sm"
                onClick={() => {
                  setStatusFilter(filter.value);
                  setPage(1);
                }}
              >
                {filter.label}
              </Button>
            ))}
          </div>
        </FadeIn>

        {/* ── Campaign List ── */}
        {loading ? (
          <Card>
            <CardContent className="pt-6 space-y-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="size-10 rounded-lg" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-48" />
                    <Skeleton className="h-3 w-72" />
                  </div>
                  <Skeleton className="h-8 w-20" />
                </div>
              ))}
            </CardContent>
          </Card>
        ) : campaigns.length === 0 ? (
          <FadeIn>
            <Card>
              <CardContent className="pt-12 pb-12 text-center">
                <div className="mx-auto size-12 rounded-full bg-muted flex items-center justify-center mb-4">
                  <Megaphone className="size-6 text-muted-foreground" />
                </div>
                <h3 className="font-heading font-semibold text-lg">
                  {statusFilter
                    ? `No ${statusFilter} campaigns`
                    : "No campaigns yet"}
                </h3>
                <p className="text-muted-foreground text-sm mt-1 max-w-sm mx-auto">
                  {statusFilter
                    ? "Try selecting a different status filter."
                    : "Create your first email campaign to start reaching your subscribers."}
                </p>
                {!statusFilter && (
                  <Button className="mt-4" onClick={() => setCreateOpen(true)}>
                    <Plus className="size-4" />
                    Create your first campaign
                  </Button>
                )}
              </CardContent>
            </Card>
          </FadeIn>
        ) : (
          <StaggerChildren className="space-y-3" staggerDelay={0.05}>
            {campaigns.map((campaign) => (
              <Card key={campaign.id} className="py-4">
                <CardContent className="flex items-center gap-4">
                  {/* Campaign icon */}
                  <div
                    className={cn(
                      "size-10 rounded-lg flex items-center justify-center shrink-0",
                      campaign.status === "sent"
                        ? "bg-emerald-100 dark:bg-emerald-900/30"
                        : campaign.status === "scheduled"
                          ? "bg-primary/10"
                          : "bg-amber-100 dark:bg-amber-900/30"
                    )}
                  >
                    <StatusIcon status={campaign.status} />
                  </div>

                  {/* Campaign details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium truncate">{campaign.name}</p>
                      <Badge variant={statusVariant(campaign.status)}>
                        {campaign.status}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
                      <span className="truncate max-w-[200px]">
                        Subject: {campaign.subject}
                      </span>
                      {campaign.sent_at && (
                        <span>Sent {formatDate(campaign.sent_at)}</span>
                      )}
                      {campaign.scheduled_at && campaign.status === "scheduled" && (
                        <span>
                          Scheduled {formatDate(campaign.scheduled_at)}
                        </span>
                      )}
                      {campaign.status === "sent" && (
                        <span>
                          {campaign.sent_count.toLocaleString()} delivered
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Action buttons */}
                  <div className="flex items-center gap-1 shrink-0">
                    {campaign.status === "sent" ? (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleViewAnalytics(campaign.id)}
                      >
                        <BarChart3 className="size-4" />
                        <span className="hidden sm:inline">Analytics</span>
                      </Button>
                    ) : (
                      <>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8"
                          onClick={() => openEditDialog(campaign)}
                          title="Edit campaign"
                        >
                          <Pencil className="size-3.5" />
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => setSendTarget(campaign)}
                          title="Send campaign"
                        >
                          <Send className="size-3.5" />
                          <span className="hidden sm:inline">Send</span>
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8 text-muted-foreground hover:text-destructive"
                          onClick={() => setDeleteTarget(campaign)}
                          title="Delete campaign"
                        >
                          <Trash2 className="size-3.5" />
                        </Button>
                      </>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </StaggerChildren>
        )}

        {/* ── Pagination ── */}
        {!loading && campaigns.length > 0 && (
          <FadeIn>
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Showing {(page - 1) * pageSize + 1} -{" "}
                {Math.min(page * pageSize, totalCampaigns)} of{" "}
                {totalCampaigns.toLocaleString()} campaigns
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  <ChevronLeft className="size-4" />
                  Previous
                </Button>
                <span className="text-sm text-muted-foreground px-2">
                  Page {page} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                  <ChevronRight className="size-4" />
                </Button>
              </div>
            </div>
          </FadeIn>
        )}

        {/* ── Error Message ── */}
        {error && (
          <FadeIn>
            <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          </FadeIn>
        )}

        {/* ── Create Campaign Dialog ── */}
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>New Campaign</DialogTitle>
              <DialogDescription>
                Create a new email campaign. You can send it immediately or
                schedule it for later.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <label
                  htmlFor="campaign-name"
                  className="text-sm font-medium"
                >
                  Campaign Name *
                </label>
                <Input
                  id="campaign-name"
                  placeholder="e.g. Spring Sale Announcement"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <label
                  htmlFor="campaign-subject"
                  className="text-sm font-medium"
                >
                  Email Subject *
                </label>
                <Input
                  id="campaign-subject"
                  placeholder="e.g. Don't miss our spring deals!"
                  value={newSubject}
                  onChange={(e) => setNewSubject(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <label
                  htmlFor="campaign-schedule"
                  className="text-sm font-medium"
                >
                  Schedule (optional)
                </label>
                <Input
                  id="campaign-schedule"
                  type="datetime-local"
                  value={newScheduledAt}
                  onChange={(e) => setNewScheduledAt(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Leave empty to create as draft. Set a date to schedule.
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setCreateOpen(false)}
                disabled={creating}
              >
                Cancel
              </Button>
              <Button onClick={handleCreate} disabled={creating}>
                {creating && <Loader2 className="size-4 animate-spin" />}
                {creating ? "Creating..." : "Create Campaign"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* ── Edit Campaign Dialog ── */}
        <Dialog
          open={editTarget !== null}
          onOpenChange={(open) => {
            if (!open) setEditTarget(null);
          }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Edit Campaign</DialogTitle>
              <DialogDescription>
                Update the campaign name and subject line.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <label htmlFor="edit-name" className="text-sm font-medium">
                  Campaign Name
                </label>
                <Input
                  id="edit-name"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="edit-subject" className="text-sm font-medium">
                  Email Subject
                </label>
                <Input
                  id="edit-subject"
                  value={editSubject}
                  onChange={(e) => setEditSubject(e.target.value)}
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setEditTarget(null)}
                disabled={saving}
              >
                Cancel
              </Button>
              <Button onClick={handleSaveEdit} disabled={saving}>
                {saving && <Loader2 className="size-4 animate-spin" />}
                {saving ? "Saving..." : "Save Changes"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* ── Send Confirmation Dialog ── */}
        <Dialog
          open={sendTarget !== null}
          onOpenChange={(open) => {
            if (!open) setSendTarget(null);
          }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Send Campaign</DialogTitle>
              <DialogDescription>
                Are you sure you want to send{" "}
                <strong>&quot;{sendTarget?.name}&quot;</strong>? This will
                deliver the email to all subscribed contacts. This action
                cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setSendTarget(null)}
                disabled={sending}
              >
                Cancel
              </Button>
              <Button
                onClick={() => sendTarget && handleSend(sendTarget.id)}
                disabled={sending}
              >
                {sending && <Loader2 className="size-4 animate-spin" />}
                {sending ? "Sending..." : "Confirm Send"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* ── Delete Confirmation Dialog ── */}
        <Dialog
          open={deleteTarget !== null}
          onOpenChange={(open) => {
            if (!open) setDeleteTarget(null);
          }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Delete Campaign</DialogTitle>
              <DialogDescription>
                Are you sure you want to delete{" "}
                <strong>&quot;{deleteTarget?.name}&quot;</strong>? This action
                cannot be undone.
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
                {deleting ? "Deleting..." : "Delete Campaign"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* ── Analytics Dialog ── */}
        <Dialog
          open={analyticsTarget !== null}
          onOpenChange={(open) => {
            if (!open) setAnalyticsTarget(null);
          }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                Campaign Analytics
              </DialogTitle>
              <DialogDescription>
                Performance metrics for{" "}
                <strong>{analyticsTarget?.campaign_name}</strong>.
              </DialogDescription>
            </DialogHeader>
            {analyticsTarget && (
              <div className="grid grid-cols-2 gap-4 py-4">
                <div className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Total Sent
                  </p>
                  <p className="text-2xl font-bold font-heading">
                    {analyticsTarget.total_sent.toLocaleString()}
                  </p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Opens
                  </p>
                  <p className="text-2xl font-bold font-heading text-emerald-600 dark:text-emerald-400">
                    {analyticsTarget.total_opened.toLocaleString()}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {analyticsTarget.open_rate.toFixed(1)}% open rate
                  </p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Clicks
                  </p>
                  <p className="text-2xl font-bold font-heading text-blue-600 dark:text-blue-400">
                    {analyticsTarget.total_clicked.toLocaleString()}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {analyticsTarget.click_rate.toFixed(1)}% click rate
                  </p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Bounces
                  </p>
                  <p className="text-2xl font-bold font-heading text-red-600 dark:text-red-400">
                    {analyticsTarget.total_bounced.toLocaleString()}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {analyticsTarget.bounce_rate.toFixed(1)}% bounce rate
                  </p>
                </div>
              </div>
            )}
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setAnalyticsTarget(null)}
              >
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageTransition>
    </Shell>
  );
}
