/**
 * Create new SMS campaign page — compose and schedule SMS blasts.
 *
 * Provides a form to create an SMS campaign with a name, body text,
 * optional contact list selector, and scheduling options. Validates
 * input client-side before submitting to the API.
 *
 * **For Developers:**
 *   - `POST /api/v1/sms/campaigns` — create a new SMS campaign.
 *   - `GET /api/v1/contacts?page_size=100` — fetch contact lists for the selector.
 *   - Body max length is 1600 characters (10x standard SMS for concatenated messages).
 *   - After creation, navigates to /sms using Next.js router.
 *   - Character counter shows remaining chars and changes color near limit.
 *
 * **For Project Managers:**
 *   - The form is intentionally simple: name, body, optional list, optional schedule.
 *   - Scheduling allows merchants to time-zone-optimize their SMS blasts.
 *   - The 1600 char limit supports multi-segment SMS (10 segments of 160 chars).
 *
 * **For QA Engineers:**
 *   - Verify validation: name required, body required, body <= 1600 chars.
 *   - Test character counter updates in real time and shows correct remaining count.
 *   - Verify the schedule toggle shows/hides the datetime picker.
 *   - Test form submission with API errors (e.g. 422 validation).
 *   - Verify redirect to /sms after successful creation.
 *   - Test with empty contact list (should still allow creation).
 *
 * **For End Users:**
 *   - Enter your campaign name and SMS message body.
 *   - Optionally select a contact list to target.
 *   - Choose to send now or schedule for later.
 *   - The character counter helps you stay within SMS limits.
 */

"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  MessageSquare,
  ArrowLeft,
  Loader2,
  CalendarClock,
  Send,
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
import { FadeIn, PageTransition } from "@/components/motion";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

/** Maximum character count for an SMS campaign body (10 concatenated segments). */
const MAX_BODY_LENGTH = 1600;

/**
 * Contact list shape for the selector dropdown.
 */
interface ContactList {
  id: string;
  name: string;
  contact_count: number;
}

/**
 * Create new SMS campaign page component.
 *
 * Renders a form with campaign name, body textarea with character counter,
 * contact list selector, and schedule toggle with datetime picker.
 *
 * @returns The new SMS campaign form page wrapped in the Shell layout.
 */
export default function NewSmsCampaignPage() {
  const router = useRouter();

  /* ── Form state ── */
  const [name, setName] = React.useState("");
  const [body, setBody] = React.useState("");
  const [contactListId, setContactListId] = React.useState("");
  const [scheduleEnabled, setScheduleEnabled] = React.useState(false);
  const [scheduledAt, setScheduledAt] = React.useState("");

  /* ── Contact lists ── */
  const [contactLists, setContactLists] = React.useState<ContactList[]>([]);
  const [listsLoading, setListsLoading] = React.useState(true);

  /* ── Submission state ── */
  const [creating, setCreating] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

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

  /** Fetch available contact lists on mount. */
  React.useEffect(() => {
    async function fetchLists() {
      const { data } = await api.get<{ items: ContactList[] }>(
        "/api/v1/contacts/lists?page_size=100"
      );
      if (data?.items) {
        setContactLists(data.items);
      }
      setListsLoading(false);
    }
    fetchLists();
  }, []);

  /** Remaining character count for the body text. */
  const charsRemaining = MAX_BODY_LENGTH - body.length;

  /** Number of SMS segments this message will use (160 chars each). */
  const segmentCount = body.length === 0 ? 0 : Math.ceil(body.length / 160);

  /**
   * Determine the color class for the character counter.
   *
   * @returns Tailwind text color class based on remaining characters.
   */
  function counterColor(): string {
    if (charsRemaining < 0) return "text-red-500";
    if (charsRemaining < 160) return "text-amber-500";
    return "text-muted-foreground";
  }

  /**
   * Validate form inputs before submission.
   *
   * @returns True if all required fields are valid, false otherwise.
   */
  function validate(): boolean {
    if (!name.trim()) {
      setError("Campaign name is required.");
      return false;
    }
    if (!body.trim()) {
      setError("SMS body is required.");
      return false;
    }
    if (body.length > MAX_BODY_LENGTH) {
      setError(`SMS body cannot exceed ${MAX_BODY_LENGTH} characters.`);
      return false;
    }
    if (scheduleEnabled && !scheduledAt) {
      setError("Please select a scheduled date and time.");
      return false;
    }
    return true;
  }

  /**
   * Submit the new SMS campaign to the API.
   * On success, shows a toast and redirects to /sms.
   */
  async function handleCreate() {
    if (!validate()) return;

    setCreating(true);
    setError(null);

    const payload: Record<string, unknown> = {
      name: name.trim(),
      body: body.trim(),
    };
    if (contactListId) payload.contact_list_id = contactListId;
    if (scheduleEnabled && scheduledAt) payload.scheduled_at = scheduledAt;

    const { error: apiError } = await api.post("/api/v1/sms/campaigns", payload);
    setCreating(false);

    if (apiError) {
      setError(apiError.message);
      showToast(apiError.message, "error");
      return;
    }

    showToast("SMS campaign created successfully!", "success");
    /* Brief delay so the user sees the toast before redirect */
    setTimeout(() => router.push("/sms"), 600);
  }

  return (
    <Shell>
      <PageTransition className="p-6 space-y-8 max-w-3xl">
        {/* ── Back link and header ── */}
        <FadeIn direction="down">
          <div>
            <Button asChild variant="ghost" size="sm" className="mb-4">
              <Link href="/sms">
                <ArrowLeft className="size-4" />
                Back to SMS Campaigns
              </Link>
            </Button>
            <div className="flex items-center gap-3">
              <div className="size-10 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
                <MessageSquare className="size-5 text-emerald-600 dark:text-emerald-400" />
              </div>
              <div>
                <h2 className="font-heading text-2xl font-bold tracking-tight">
                  New SMS Campaign
                </h2>
                <p className="text-muted-foreground mt-0.5">
                  Compose an SMS message to send to your contacts.
                </p>
              </div>
            </div>
          </div>
        </FadeIn>

        {/* ── Campaign Form ── */}
        <FadeIn delay={0.1}>
          <Card>
            <CardHeader>
              <CardTitle>Campaign Details</CardTitle>
              <CardDescription>
                Configure your SMS campaign name and message content.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Campaign Name */}
              <div className="space-y-2">
                <label htmlFor="sms-name" className="text-sm font-medium">
                  Campaign Name <span className="text-destructive">*</span>
                </label>
                <Input
                  id="sms-name"
                  placeholder="e.g. Flash Sale Alert"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>

              {/* SMS Body */}
              <div className="space-y-2">
                <label htmlFor="sms-body" className="text-sm font-medium">
                  SMS Body <span className="text-destructive">*</span>
                </label>
                <textarea
                  id="sms-body"
                  rows={6}
                  maxLength={MAX_BODY_LENGTH}
                  placeholder="Type your SMS message here..."
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background resize-y min-h-[120px]"
                />
                <div className="flex items-center justify-between">
                  <p className="text-xs text-muted-foreground">
                    {segmentCount > 0 && (
                      <span>
                        {segmentCount} SMS segment{segmentCount !== 1 ? "s" : ""}
                        {" "}
                      </span>
                    )}
                  </p>
                  <p className={cn("text-xs tabular-nums", counterColor())}>
                    {charsRemaining.toLocaleString()} / {MAX_BODY_LENGTH.toLocaleString()} characters remaining
                  </p>
                </div>
              </div>

              {/* Contact List Selector */}
              <div className="space-y-2">
                <label htmlFor="sms-list" className="text-sm font-medium">
                  Contact List{" "}
                  <span className="text-muted-foreground font-normal">(optional)</span>
                </label>
                {listsLoading ? (
                  <div className="h-10 rounded-md border border-input bg-muted animate-pulse" />
                ) : (
                  <select
                    id="sms-list"
                    value={contactListId}
                    onChange={(e) => setContactListId(e.target.value)}
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background"
                  >
                    <option value="">All contacts</option>
                    {contactLists.map((list) => (
                      <option key={list.id} value={list.id}>
                        {list.name} ({list.contact_count} contacts)
                      </option>
                    ))}
                  </select>
                )}
                <p className="text-xs text-muted-foreground">
                  Leave empty to send to all subscribed contacts.
                </p>
              </div>
            </CardContent>
          </Card>
        </FadeIn>

        {/* ── Schedule Section ── */}
        <FadeIn delay={0.2}>
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <CalendarClock className="size-5 text-muted-foreground" />
                <div className="flex-1">
                  <CardTitle>Schedule</CardTitle>
                  <CardDescription>
                    Send now or schedule for a specific date and time.
                  </CardDescription>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={scheduleEnabled}
                  onClick={() => setScheduleEnabled(!scheduleEnabled)}
                  className={cn(
                    "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
                    scheduleEnabled ? "bg-emerald-500" : "bg-muted"
                  )}
                >
                  <span
                    className={cn(
                      "inline-block size-4 rounded-full bg-white transition-transform",
                      scheduleEnabled ? "translate-x-6" : "translate-x-1"
                    )}
                  />
                </button>
              </div>
            </CardHeader>
            {scheduleEnabled && (
              <CardContent>
                <div className="space-y-2">
                  <label htmlFor="sms-schedule" className="text-sm font-medium">
                    Send Date & Time
                  </label>
                  <Input
                    id="sms-schedule"
                    type="datetime-local"
                    value={scheduledAt}
                    onChange={(e) => setScheduledAt(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    The campaign will be sent automatically at the specified time.
                  </p>
                </div>
              </CardContent>
            )}
          </Card>
        </FadeIn>

        {/* ── Error Message ── */}
        {error && (
          <FadeIn>
            <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          </FadeIn>
        )}

        {/* ── Submit Button ── */}
        <FadeIn delay={0.3}>
          <div className="flex items-center gap-3">
            <Button
              onClick={handleCreate}
              disabled={creating}
              size="lg"
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              {creating ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Send className="size-4" />
              )}
              {creating
                ? "Creating..."
                : scheduleEnabled
                  ? "Schedule Campaign"
                  : "Create Campaign"}
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link href="/sms">Cancel</Link>
            </Button>
          </div>
        </FadeIn>

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
      </PageTransition>
    </Shell>
  );
}
