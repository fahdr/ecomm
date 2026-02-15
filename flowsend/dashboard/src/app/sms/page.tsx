/**
 * SMS Campaigns page — list, send, and manage SMS marketing campaigns.
 *
 * Displays a paginated list of SMS campaigns with status badges,
 * delivery metrics, and action buttons. Includes summary KPI cards
 * showing campaign counts and delivery rates.
 *
 * **For Developers:**
 *   - `GET /api/v1/sms/campaigns?page=&page_size=` — paginated campaign list.
 *   - `POST /api/v1/sms/campaigns/:id/send` — send a draft campaign.
 *   - Status lifecycle: draft -> sending -> sent, draft -> scheduled -> sending -> sent.
 *   - Uses the same Shell layout, motion components, and api helper as email campaigns.
 *
 * **For Project Managers:**
 *   - SMS campaigns complement the existing email marketing feature.
 *   - The send flow mirrors email campaigns with a confirmation dialog.
 *   - SMS-specific green accent differentiates from email's purple/blue palette.
 *
 * **For QA Engineers:**
 *   - Test with 0 campaigns (empty state), draft, sending, sent, and scheduled statuses.
 *   - Verify draft campaigns show the Send button; sent campaigns do not.
 *   - Verify pagination controls appear only when campaigns exist.
 *   - Test with API errors to verify error state rendering.
 *
 * **For End Users:**
 *   - View all your SMS campaigns at a glance with delivery statistics.
 *   - Create new campaigns with the "New Campaign" button.
 *   - Send draft campaigns directly from the list.
 */

"use client";

import * as React from "react";
import Link from "next/link";
import {
  MessageSquare,
  Plus,
  Send,
  Loader2,
  CheckCircle2,
  FileEdit,
  ChevronLeft,
  ChevronRight,
  Clock,
  Radio,
  Percent,
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

/** Shape of an SMS campaign as returned by the API. */
interface SmsCampaign {
  id: string;
  name: string;
  body: string;
  status: string;
  scheduled_at: string | null;
  sent_at: string | null;
  total_recipients: number;
  sent_count: number;
  delivered_count: number;
  failed_count: number;
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

/**
 * Map an SMS campaign status to a Badge variant.
 *
 * @param status - The campaign status string.
 * @returns The appropriate badge variant for visual distinction.
 */
function statusVariant(
  status: string
): "default" | "secondary" | "success" | "destructive" | "outline" {
  switch (status) {
    case "sent":
      return "success";
    case "sending":
      return "default";
    case "scheduled":
      return "outline";
    case "draft":
      return "secondary";
    default:
      return "outline";
  }
}

/**
 * Return a status-specific background color class for the campaign icon.
 *
 * @param status - The campaign status string.
 * @returns Tailwind CSS class for the icon background.
 */
function statusIconBg(status: string): string {
  switch (status) {
    case "sent":
      return "bg-emerald-100 dark:bg-emerald-900/30";
    case "sending":
      return "bg-blue-100 dark:bg-blue-900/30";
    case "scheduled":
      return "bg-amber-100 dark:bg-amber-900/30";
    case "draft":
      return "bg-zinc-100 dark:bg-zinc-800/50";
    default:
      return "bg-zinc-100 dark:bg-zinc-800/50";
  }
}

/**
 * Render the appropriate icon for a campaign status.
 *
 * @param props - Object containing the status string.
 * @returns A React element with the status icon.
 */
function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case "sent":
      return <CheckCircle2 className="size-3.5 text-emerald-600 dark:text-emerald-400" />;
    case "sending":
      return <Radio className="size-3.5 text-blue-600 dark:text-blue-400 animate-pulse" />;
    case "scheduled":
      return <Clock className="size-3.5 text-amber-600 dark:text-amber-400" />;
    case "draft":
      return <FileEdit className="size-3.5 text-zinc-500" />;
    default:
      return <MessageSquare className="size-3.5 text-zinc-500" />;
  }
}

/**
 * SMS Campaigns page component.
 *
 * Fetches and displays SMS campaigns with KPI summary cards, a paginated
 * campaign list, send confirmation dialog, and empty state handling.
 *
 * @returns The SMS campaigns page wrapped in the Shell layout.
 */
export default function SmsCampaignsPage() {
  /* ── List state ── */
  const [campaigns, setCampaigns] = React.useState<SmsCampaign[]>([]);
  const [totalCampaigns, setTotalCampaigns] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [pageSize] = React.useState(20);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  /* ── Send confirmation state ── */
  const [sendTarget, setSendTarget] = React.useState<SmsCampaign | null>(null);
  const [sending, setSending] = React.useState(false);

  /* ── Toast state ── */
  const [toast, setToast] = React.useState<{ message: string; type: "success" | "error" } | null>(null);

  /**
   * Show a toast notification that auto-dismisses after 3 seconds.
   *
   * @param message - The message to display.
   * @param type - Whether this is a success or error toast.
   */
  function showToast(message: string, type: "success" | "error") {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  }

  /**
   * Fetch SMS campaigns from the API with current pagination.
   */
  async function fetchCampaigns() {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });

    const { data, error: apiError } = await api.get<
      PaginatedResponse<SmsCampaign>
    >(`/api/v1/sms/campaigns?${params.toString()}`);
    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setCampaigns(data.items);
      setTotalCampaigns(data.total);
    }
    setLoading(false);
  }

  /** Fetch on mount and when page changes. */
  React.useEffect(() => {
    fetchCampaigns();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  /**
   * Send an SMS campaign after user confirmation.
   *
   * @param id - The campaign UUID.
   */
  async function handleSend(id: string) {
    setSending(true);
    setError(null);

    const { error: apiError } = await api.post(
      `/api/v1/sms/campaigns/${id}/send`
    );
    setSending(false);

    if (apiError) {
      showToast(apiError.message, "error");
      return;
    }

    setSendTarget(null);
    showToast("SMS campaign sent successfully!", "success");
    fetchCampaigns();
  }

  /** Calculate pagination values. */
  const totalPages = Math.max(1, Math.ceil(totalCampaigns / pageSize));

  /** Count campaigns by status for KPI cards. */
  const draftCount = campaigns.filter((c) => c.status === "draft").length;
  const sentCount = campaigns.filter((c) => c.status === "sent").length;

  /** Calculate average delivery rate across sent campaigns. */
  const sentCampaigns = campaigns.filter((c) => c.status === "sent" && c.sent_count > 0);
  const avgDeliveryRate =
    sentCampaigns.length > 0
      ? Math.round(
          sentCampaigns.reduce(
            (acc, c) => acc + (c.delivered_count / c.sent_count) * 100,
            0
          ) / sentCampaigns.length
        )
      : 0;

  /**
   * Format an ISO date string for display.
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
                SMS Campaigns
              </h2>
              <p className="text-muted-foreground mt-1">
                Create and send SMS marketing campaigns to your contacts.
              </p>
            </div>
            <Button asChild>
              <Link href="/sms/new">
                <Plus className="size-4" />
                New Campaign
              </Link>
            </Button>
          </div>
        </FadeIn>

        {/* ── KPI Summary Cards ── */}
        <StaggerChildren
          className="grid grid-cols-1 md:grid-cols-4 gap-4"
          staggerDelay={0.08}
        >
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Campaigns
              </CardTitle>
              <MessageSquare className="size-4 text-muted-foreground" />
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

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Draft
              </CardTitle>
              <FileEdit className="size-4 text-zinc-400" />
            </CardHeader>
            <CardContent>
              <AnimatedCounter
                value={draftCount}
                className="text-3xl font-bold font-heading text-zinc-500 dark:text-zinc-400"
              />
              <p className="text-xs text-muted-foreground mt-1">
                ready to send
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Delivery Rate
              </CardTitle>
              <Percent className="size-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              <div className="flex items-baseline gap-1">
                <AnimatedCounter
                  value={avgDeliveryRate}
                  className="text-3xl font-bold font-heading text-emerald-600 dark:text-emerald-400"
                />
                <span className="text-lg font-semibold text-emerald-600 dark:text-emerald-400">
                  %
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                avg across sent
              </p>
            </CardContent>
          </Card>
        </StaggerChildren>

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
                <div className="mx-auto size-12 rounded-full bg-emerald-100 dark:bg-emerald-900/20 flex items-center justify-center mb-4">
                  <MessageSquare className="size-6 text-emerald-600 dark:text-emerald-400" />
                </div>
                <h3 className="font-heading font-semibold text-lg">
                  No SMS campaigns yet
                </h3>
                <p className="text-muted-foreground text-sm mt-1 max-w-sm mx-auto">
                  Create your first SMS campaign to start reaching your
                  contacts via text message.
                </p>
                <Button className="mt-4" asChild>
                  <Link href="/sms/new">
                    <Plus className="size-4" />
                    Create your first SMS campaign
                  </Link>
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        ) : (
          <FadeIn delay={0.2}>
            <Card>
              <CardContent className="pt-4">
                {/* Table header */}
                <div className="grid grid-cols-[1fr_auto_auto_auto_auto_auto] gap-4 px-4 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider border-b">
                  <span>Name</span>
                  <span>Status</span>
                  <span className="text-right">Recipients</span>
                  <span className="text-right">Sent</span>
                  <span>Created</span>
                  <span className="text-right">Actions</span>
                </div>

                {/* Table rows */}
                <div className="divide-y">
                  {campaigns.map((campaign) => (
                    <div
                      key={campaign.id}
                      className="grid grid-cols-[1fr_auto_auto_auto_auto_auto] gap-4 px-4 py-3 items-center hover:bg-muted/50 transition-colors"
                    >
                      {/* Campaign name + icon */}
                      <div className="flex items-center gap-3 min-w-0">
                        <div
                          className={cn(
                            "size-9 rounded-lg flex items-center justify-center shrink-0",
                            statusIconBg(campaign.status)
                          )}
                        >
                          <StatusIcon status={campaign.status} />
                        </div>
                        <div className="min-w-0">
                          <p className="font-medium truncate text-sm">
                            {campaign.name}
                          </p>
                          <p className="text-xs text-muted-foreground truncate max-w-[250px]">
                            {campaign.body.length > 60
                              ? campaign.body.slice(0, 60) + "..."
                              : campaign.body}
                          </p>
                        </div>
                      </div>

                      {/* Status badge */}
                      <Badge variant={statusVariant(campaign.status)}>
                        {campaign.status}
                      </Badge>

                      {/* Recipients */}
                      <span className="text-sm text-muted-foreground text-right tabular-nums">
                        {campaign.total_recipients.toLocaleString()}
                      </span>

                      {/* Sent count */}
                      <span className="text-sm text-muted-foreground text-right tabular-nums">
                        {campaign.sent_count.toLocaleString()}
                      </span>

                      {/* Created date */}
                      <span className="text-xs text-muted-foreground whitespace-nowrap">
                        {formatDate(campaign.created_at)}
                      </span>

                      {/* Actions */}
                      <div className="flex items-center gap-1 justify-end">
                        {campaign.status === "draft" && (
                          <Button
                            size="sm"
                            onClick={() => setSendTarget(campaign)}
                            className="bg-emerald-600 hover:bg-emerald-700 text-white"
                          >
                            <Send className="size-3.5" />
                            <span className="hidden sm:inline">Send</span>
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Pagination controls */}
                <div className="flex items-center justify-between px-4 py-3 border-t">
                  <p className="text-sm text-muted-foreground">
                    Showing {(page - 1) * pageSize + 1}
                    {" - "}
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
              </CardContent>
            </Card>
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

        {/* ── Toast Notification ── */}
        {toast && (
          <div
            className={cn(
              "fixed bottom-6 right-6 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium transition-all duration-300",
              toast.type === "success"
                ? "bg-emerald-600 text-white"
                : "bg-destructive text-destructive-foreground"
            )}
          >
            {toast.message}
          </div>
        )}

        {/* ── Send Confirmation Dialog ── */}
        <Dialog
          open={sendTarget !== null}
          onOpenChange={(open) => {
            if (!open) setSendTarget(null);
          }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Send SMS Campaign</DialogTitle>
              <DialogDescription>
                Are you sure you want to send{" "}
                <strong>&quot;{sendTarget?.name}&quot;</strong>? This will
                deliver the SMS to all targeted contacts. This action cannot
                be undone.
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
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
              >
                {sending && <Loader2 className="size-4 animate-spin" />}
                {sending ? "Sending..." : "Confirm Send"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageTransition>
    </Shell>
  );
}
