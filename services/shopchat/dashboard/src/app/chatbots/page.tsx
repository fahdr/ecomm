/**
 * Chatbot management page -- create, configure, and deploy AI chatbots.
 *
 * Provides a full CRUD interface for managing chatbots. Each chatbot
 * gets a unique widget_key for embedding on external websites. Users
 * can configure personality, welcome message, theme, and active status.
 *
 * **For Developers:**
 *   - `GET /api/v1/chatbots` -- list chatbots (paginated).
 *   - `POST /api/v1/chatbots` -- create a chatbot `{ name, personality, welcome_message, theme_config }`.
 *   - `PATCH /api/v1/chatbots/:id` -- update a chatbot.
 *   - `DELETE /api/v1/chatbots/:id` -- delete a chatbot.
 *   - The create/edit flow uses a Dialog modal with form fields.
 *   - Widget key is shown in a copyable code field on each card.
 *
 * **For Project Managers:**
 *   - Chatbots are the core entity -- each one represents an AI assistant
 *     deployed on a customer's website. This page is the primary workflow.
 *
 * **For QA Engineers:**
 *   - Verify creating a chatbot adds it to the list immediately.
 *   - Verify editing updates the chatbot in-place without page reload.
 *   - Verify deleting shows a confirmation dialog before removal.
 *   - Test empty state when no chatbots exist.
 *   - Test copying the widget key to clipboard.
 *
 * **For End Users:**
 *   - Create chatbots to deploy on your store or website.
 *   - Copy the widget key to integrate with your site.
 *   - Toggle active/inactive to control availability.
 */

"use client";

import * as React from "react";
import {
  Plus,
  Bot,
  Copy,
  Check,
  Trash2,
  Pencil,
  Loader2,
  Power,
  PowerOff,
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

/** Shape of a chatbot returned by the API. */
interface Chatbot {
  /** Unique chatbot identifier (UUID). */
  id: string;
  /** Owning user identifier. */
  user_id: string;
  /** Human-readable chatbot name. */
  name: string;
  /** Personality style (friendly, professional, casual, helpful). */
  personality: string;
  /** Greeting shown when the widget opens. */
  welcome_message: string;
  /** Widget appearance configuration. */
  theme_config: Record<string, string>;
  /** Whether the chatbot is accepting conversations. */
  is_active: boolean;
  /** Unique key used to embed the widget on external sites. */
  widget_key: string;
  /** ISO timestamp of creation. */
  created_at: string;
  /** ISO timestamp of last update. */
  updated_at: string;
}

/** Shape of the paginated response from the chatbots list endpoint. */
interface PaginatedChatbots {
  items: Chatbot[];
  total: number;
  page: number;
  page_size: number;
}

/** Personality options available for chatbot configuration. */
const PERSONALITIES = [
  { value: "friendly", label: "Friendly" },
  { value: "professional", label: "Professional" },
  { value: "casual", label: "Casual" },
  { value: "helpful", label: "Helpful" },
];

/**
 * Chatbot management page component.
 *
 * @returns The chatbot management page wrapped in the Shell layout.
 */
export default function ChatbotsPage() {
  const [chatbots, setChatbots] = React.useState<Chatbot[]>([]);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  /* Create/Edit dialog state */
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Chatbot | null>(null);
  const [formName, setFormName] = React.useState("");
  const [formPersonality, setFormPersonality] = React.useState("friendly");
  const [formWelcome, setFormWelcome] = React.useState(
    "Hi there! How can I help you today?"
  );
  const [submitting, setSubmitting] = React.useState(false);

  /* Delete confirmation dialog state */
  const [deleteTarget, setDeleteTarget] = React.useState<Chatbot | null>(null);
  const [deleting, setDeleting] = React.useState(false);

  /* Widget key copy state */
  const [copiedId, setCopiedId] = React.useState<string | null>(null);

  /**
   * Fetch chatbots from the API on mount.
   */
  React.useEffect(() => {
    fetchChatbots();
  }, []);

  /**
   * Fetch the list of chatbots from the backend.
   */
  async function fetchChatbots(): Promise<void> {
    setLoading(true);
    setError(null);
    const { data, error: apiError } =
      await api.get<PaginatedChatbots>("/api/v1/chatbots");
    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setChatbots(data.items);
      setTotal(data.total);
    }
    setLoading(false);
  }

  /**
   * Open the create dialog with empty form fields.
   */
  function handleOpenCreate(): void {
    setEditing(null);
    setFormName("");
    setFormPersonality("friendly");
    setFormWelcome("Hi there! How can I help you today?");
    setDialogOpen(true);
  }

  /**
   * Open the edit dialog pre-filled with the chatbot's current values.
   *
   * @param bot - The chatbot to edit.
   */
  function handleOpenEdit(bot: Chatbot): void {
    setEditing(bot);
    setFormName(bot.name);
    setFormPersonality(bot.personality);
    setFormWelcome(bot.welcome_message);
    setDialogOpen(true);
  }

  /**
   * Submit the create or update form.
   * Creates a new chatbot or patches an existing one.
   */
  async function handleSubmit(): Promise<void> {
    if (!formName.trim()) {
      setError("Please enter a chatbot name.");
      return;
    }
    setSubmitting(true);
    setError(null);

    if (editing) {
      /* Update existing chatbot */
      const { error: apiError } = await api.patch<Chatbot>(
        `/api/v1/chatbots/${editing.id}`,
        {
          name: formName.trim(),
          personality: formPersonality,
          welcome_message: formWelcome,
        }
      );
      if (apiError) {
        setError(apiError.message);
        setSubmitting(false);
        return;
      }
    } else {
      /* Create new chatbot */
      const { error: apiError } = await api.post<Chatbot>("/api/v1/chatbots", {
        name: formName.trim(),
        personality: formPersonality,
        welcome_message: formWelcome,
      });
      if (apiError) {
        setError(apiError.message);
        setSubmitting(false);
        return;
      }
    }

    setSubmitting(false);
    setDialogOpen(false);
    fetchChatbots();
  }

  /**
   * Toggle a chatbot's active status.
   *
   * @param bot - The chatbot to toggle.
   */
  async function handleToggleActive(bot: Chatbot): Promise<void> {
    const { error: apiError } = await api.patch<Chatbot>(
      `/api/v1/chatbots/${bot.id}`,
      { is_active: !bot.is_active }
    );
    if (apiError) {
      setError(apiError.message);
      return;
    }
    fetchChatbots();
  }

  /**
   * Delete a chatbot after confirmation.
   *
   * @param id - The chatbot UUID to delete.
   */
  async function handleDelete(id: string): Promise<void> {
    setDeleting(true);
    const { error: apiError } = await api.del(`/api/v1/chatbots/${id}`);
    setDeleting(false);
    if (apiError) {
      setError(apiError.message);
      return;
    }
    setDeleteTarget(null);
    fetchChatbots();
  }

  /**
   * Copy a chatbot's widget key to the clipboard.
   *
   * @param bot - The chatbot whose widget key to copy.
   */
  async function handleCopyKey(bot: Chatbot): Promise<void> {
    await navigator.clipboard.writeText(bot.widget_key);
    setCopiedId(bot.id);
    setTimeout(() => setCopiedId(null), 2000);
  }

  /**
   * Format an ISO date string for display.
   *
   * @param dateStr - ISO date string.
   * @returns Formatted date string.
   */
  function formatDate(dateStr: string): string {
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
                Chatbots
              </h2>
              <p className="text-muted-foreground mt-1">
                Create and manage your AI shopping assistants.
              </p>
            </div>
            <Button onClick={handleOpenCreate}>
              <Plus className="size-4" />
              Create Chatbot
            </Button>
          </div>
        </FadeIn>

        {/* -- Error Banner -- */}
        {error && (
          <FadeIn>
            <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          </FadeIn>
        )}

        {/* -- Loading State -- */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {Array.from({ length: 3 }).map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-5 w-32" />
                  <Skeleton className="h-3 w-48 mt-2" />
                </CardHeader>
                <CardContent className="space-y-3">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-2/3" />
                  <Skeleton className="h-8 w-24 mt-2" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : chatbots.length === 0 ? (
          /* -- Empty State -- */
          <FadeIn>
            <Card>
              <CardContent className="pt-12 pb-12 text-center">
                <div className="mx-auto size-14 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                  <Bot className="size-7 text-primary" />
                </div>
                <h3 className="font-heading font-semibold text-lg">
                  No chatbots yet
                </h3>
                <p className="text-muted-foreground text-sm mt-1 max-w-md mx-auto">
                  Create your first AI chatbot to start helping your customers
                  with instant support and product recommendations.
                </p>
                <Button className="mt-5" onClick={handleOpenCreate}>
                  <Plus className="size-4" />
                  Create your first chatbot
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        ) : (
          /* -- Chatbot Cards Grid -- */
          <StaggerChildren
            className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6"
            staggerDelay={0.08}
          >
            {chatbots.map((bot) => (
              <Card key={bot.id} className="relative group">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="size-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                        <Bot className="size-5 text-primary" />
                      </div>
                      <div className="min-w-0">
                        <CardTitle className="text-base truncate">
                          {bot.name}
                        </CardTitle>
                        <CardDescription className="text-xs mt-0.5">
                          Created {formatDate(bot.created_at)}
                        </CardDescription>
                      </div>
                    </div>
                    <Badge
                      variant={bot.is_active ? "success" : "secondary"}
                      className="shrink-0"
                    >
                      {bot.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </div>
                </CardHeader>

                <CardContent className="space-y-4">
                  {/* Personality */}
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-muted-foreground">Personality:</span>
                    <Badge variant="outline" className="capitalize text-xs">
                      {bot.personality}
                    </Badge>
                  </div>

                  {/* Welcome Message */}
                  <p className="text-sm text-muted-foreground line-clamp-2 italic">
                    &ldquo;{bot.welcome_message}&rdquo;
                  </p>

                  {/* Widget Key */}
                  <div className="flex items-center gap-2">
                    <code className="flex-1 bg-muted rounded-md px-2.5 py-1.5 text-xs font-mono truncate">
                      {bot.widget_key}
                    </code>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="shrink-0 size-8"
                      onClick={() => handleCopyKey(bot)}
                    >
                      {copiedId === bot.id ? (
                        <Check className="size-3.5 text-emerald-600" />
                      ) : (
                        <Copy className="size-3.5" />
                      )}
                    </Button>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 pt-1">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleOpenEdit(bot)}
                    >
                      <Pencil className="size-3.5" />
                      Edit
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleToggleActive(bot)}
                      className={
                        bot.is_active
                          ? "text-amber-600 hover:text-amber-700"
                          : "text-emerald-600 hover:text-emerald-700"
                      }
                    >
                      {bot.is_active ? (
                        <>
                          <PowerOff className="size-3.5" />
                          Deactivate
                        </>
                      ) : (
                        <>
                          <Power className="size-3.5" />
                          Activate
                        </>
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-muted-foreground hover:text-destructive ml-auto"
                      onClick={() => setDeleteTarget(bot)}
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </StaggerChildren>
        )}

        {/* -- Total count -- */}
        {!loading && chatbots.length > 0 && (
          <FadeIn delay={0.3}>
            <p className="text-sm text-muted-foreground text-center">
              Showing {chatbots.length} of {total} chatbot{total !== 1 ? "s" : ""}
            </p>
          </FadeIn>
        )}

        {/* -- Create/Edit Dialog -- */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                {editing ? "Edit Chatbot" : "Create Chatbot"}
              </DialogTitle>
              <DialogDescription>
                {editing
                  ? "Update your chatbot's configuration."
                  : "Configure your new AI shopping assistant."}
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2">
              {/* Name */}
              <div className="space-y-2">
                <label htmlFor="bot-name" className="text-sm font-medium">
                  Name
                </label>
                <Input
                  id="bot-name"
                  placeholder="e.g. Store Assistant"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                />
              </div>

              {/* Personality */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Personality</label>
                <div className="grid grid-cols-2 gap-2">
                  {PERSONALITIES.map((p) => (
                    <button
                      key={p.value}
                      type="button"
                      onClick={() => setFormPersonality(p.value)}
                      className={`rounded-lg border px-3 py-2 text-sm transition-colors ${
                        formPersonality === p.value
                          ? "border-primary bg-primary/10 text-primary font-medium"
                          : "border-input hover:bg-secondary text-muted-foreground"
                      }`}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Welcome Message */}
              <div className="space-y-2">
                <label htmlFor="welcome-msg" className="text-sm font-medium">
                  Welcome Message
                </label>
                <Input
                  id="welcome-msg"
                  placeholder="Hi there! How can I help you today?"
                  value={formWelcome}
                  onChange={(e) => setFormWelcome(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Shown when a visitor opens the chat widget.
                </p>
              </div>
            </div>

            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setDialogOpen(false)}
                disabled={submitting}
              >
                Cancel
              </Button>
              <Button onClick={handleSubmit} disabled={submitting}>
                {submitting && <Loader2 className="size-4 animate-spin" />}
                {submitting
                  ? editing
                    ? "Saving..."
                    : "Creating..."
                  : editing
                    ? "Save Changes"
                    : "Create Chatbot"}
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
              <DialogTitle>Delete Chatbot</DialogTitle>
              <DialogDescription>
                Are you sure you want to delete{" "}
                <strong>&quot;{deleteTarget?.name}&quot;</strong>? This will
                permanently remove all conversations, knowledge base entries,
                and analytics data associated with this chatbot.
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
                {deleting ? "Deleting..." : "Delete Chatbot"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageTransition>
    </Shell>
  );
}
