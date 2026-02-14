/**
 * Knowledge base management page -- add, edit, and organize training data.
 *
 * The knowledge base is how chatbots learn about products, policies, FAQs,
 * and custom content. Each entry has a title, content body, source type,
 * and optional metadata. Entries can be filtered by chatbot and toggled
 * active/inactive.
 *
 * **For Developers:**
 *   - `GET /api/v1/knowledge` -- list entries (paginated, optional chatbot_id filter).
 *   - `POST /api/v1/knowledge` -- create entry `{ chatbot_id, title, content, source_type, metadata }`.
 *   - `PATCH /api/v1/knowledge/:id` -- update entry fields.
 *   - `DELETE /api/v1/knowledge/:id` -- remove entry.
 *   - `GET /api/v1/chatbots` -- fetch chatbot list for the chatbot selector.
 *   - Create/edit uses a Dialog modal with form fields.
 *
 * **For Project Managers:**
 *   - Knowledge base pages are a secondary billing metric.
 *   - Source types help organize content: product_catalog, policy_page, faq, custom_text, url.
 *   - Higher quality knowledge base = better AI responses.
 *
 * **For QA Engineers:**
 *   - Verify creating an entry requires selecting a chatbot.
 *   - Verify editing updates the entry without page reload.
 *   - Verify deleting shows a confirmation dialog.
 *   - Test plan limit enforcement (403 when at limit).
 *   - Test filtering by chatbot and source type.
 *   - Test empty state for new users.
 *
 * **For End Users:**
 *   - Add product information, FAQs, and policies here so your chatbot
 *     can answer customer questions accurately.
 *   - The more relevant content you add, the better your chatbot performs.
 */

"use client";

import * as React from "react";
import {
  Plus,
  BookOpen,
  Trash2,
  Pencil,
  Loader2,
  FileText,
  ShoppingBag,
  HelpCircle,
  Link2,
  ScrollText,
  ToggleLeft,
  ToggleRight,
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

/** Shape of a knowledge base entry returned by the API. */
interface KnowledgeEntry {
  /** Unique entry identifier (UUID). */
  id: string;
  /** Parent chatbot identifier. */
  chatbot_id: string;
  /** Content source type. */
  source_type: string;
  /** Human-readable entry title. */
  title: string;
  /** Full text content used for AI context. */
  content: string;
  /** Optional structured metadata. */
  metadata: Record<string, unknown> | null;
  /** Whether the entry is active and used by the AI. */
  is_active: boolean;
  /** ISO creation timestamp. */
  created_at: string;
  /** ISO last-update timestamp. */
  updated_at: string;
}

/** Paginated knowledge base response. */
interface PaginatedKnowledge {
  items: KnowledgeEntry[];
  total: number;
  page: number;
  page_size: number;
}

/** Shape of a chatbot for the selector dropdown. */
interface ChatbotOption {
  id: string;
  name: string;
}

/** Paginated chatbot response. */
interface PaginatedChatbots {
  items: ChatbotOption[];
  total: number;
  page: number;
  page_size: number;
}

/** Available source type options with labels and icons. */
const SOURCE_TYPES = [
  { value: "product_catalog", label: "Product", icon: ShoppingBag },
  { value: "policy_page", label: "Policy", icon: ScrollText },
  { value: "faq", label: "FAQ", icon: HelpCircle },
  { value: "custom_text", label: "Custom", icon: FileText },
  { value: "url", label: "URL", icon: Link2 },
] as const;

/**
 * Get the icon component for a given source type.
 *
 * @param sourceType - The source type string.
 * @returns The matching lucide-react icon component.
 */
function getSourceIcon(sourceType: string) {
  const match = SOURCE_TYPES.find((st) => st.value === sourceType);
  return match?.icon || FileText;
}

/**
 * Get the display label for a given source type.
 *
 * @param sourceType - The source type string.
 * @returns The human-readable label.
 */
function getSourceLabel(sourceType: string): string {
  const match = SOURCE_TYPES.find((st) => st.value === sourceType);
  return match?.label || sourceType;
}

/**
 * Knowledge base management page component.
 *
 * @returns The knowledge base page wrapped in the Shell layout.
 */
export default function KnowledgePage() {
  /* List state */
  const [entries, setEntries] = React.useState<KnowledgeEntry[]>([]);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  /* Chatbot filter and selector */
  const [chatbots, setChatbots] = React.useState<ChatbotOption[]>([]);
  const [filterChatbot, setFilterChatbot] = React.useState<string>("");

  /* Create/Edit dialog state */
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<KnowledgeEntry | null>(null);
  const [formChatbotId, setFormChatbotId] = React.useState("");
  const [formTitle, setFormTitle] = React.useState("");
  const [formContent, setFormContent] = React.useState("");
  const [formSourceType, setFormSourceType] = React.useState("custom_text");
  const [submitting, setSubmitting] = React.useState(false);

  /* Delete confirmation */
  const [deleteTarget, setDeleteTarget] = React.useState<KnowledgeEntry | null>(
    null
  );
  const [deleting, setDeleting] = React.useState(false);

  /**
   * Fetch chatbot options on mount.
   */
  React.useEffect(() => {
    fetchChatbots();
  }, []);

  /**
   * Re-fetch entries when filter changes.
   */
  React.useEffect(() => {
    fetchEntries();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterChatbot]);

  /**
   * Fetch the chatbot list for dropdowns.
   */
  async function fetchChatbots(): Promise<void> {
    const { data } =
      await api.get<PaginatedChatbots>("/api/v1/chatbots?page_size=100");
    if (data) {
      setChatbots(data.items);
      /* Auto-select the first chatbot for the create form if available */
      if (data.items.length > 0 && !formChatbotId) {
        setFormChatbotId(data.items[0].id);
      }
    }
  }

  /**
   * Fetch knowledge base entries from the backend.
   */
  async function fetchEntries(): Promise<void> {
    setLoading(true);
    setError(null);

    let path = "/api/v1/knowledge?page_size=100";
    if (filterChatbot) {
      path += `&chatbot_id=${filterChatbot}`;
    }

    const { data, error: apiError } =
      await api.get<PaginatedKnowledge>(path);
    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setEntries(data.items);
      setTotal(data.total);
    }
    setLoading(false);
  }

  /**
   * Open the create dialog with empty form fields.
   */
  function handleOpenCreate(): void {
    setEditing(null);
    setFormTitle("");
    setFormContent("");
    setFormSourceType("custom_text");
    if (chatbots.length > 0) {
      setFormChatbotId(filterChatbot || chatbots[0].id);
    }
    setDialogOpen(true);
  }

  /**
   * Open the edit dialog pre-filled with the entry's current values.
   *
   * @param entry - The knowledge base entry to edit.
   */
  function handleOpenEdit(entry: KnowledgeEntry): void {
    setEditing(entry);
    setFormChatbotId(entry.chatbot_id);
    setFormTitle(entry.title);
    setFormContent(entry.content);
    setFormSourceType(entry.source_type);
    setDialogOpen(true);
  }

  /**
   * Submit the create or update form.
   */
  async function handleSubmit(): Promise<void> {
    if (!formTitle.trim()) {
      setError("Please enter a title.");
      return;
    }
    if (!formContent.trim()) {
      setError("Please enter content.");
      return;
    }
    if (!formChatbotId) {
      setError("Please select a chatbot.");
      return;
    }

    setSubmitting(true);
    setError(null);

    if (editing) {
      const { error: apiError } = await api.patch<KnowledgeEntry>(
        `/api/v1/knowledge/${editing.id}`,
        {
          title: formTitle.trim(),
          content: formContent.trim(),
          source_type: formSourceType,
        }
      );
      if (apiError) {
        setError(apiError.message);
        setSubmitting(false);
        return;
      }
    } else {
      const { error: apiError } = await api.post<KnowledgeEntry>(
        "/api/v1/knowledge",
        {
          chatbot_id: formChatbotId,
          title: formTitle.trim(),
          content: formContent.trim(),
          source_type: formSourceType,
        }
      );
      if (apiError) {
        setError(apiError.message);
        setSubmitting(false);
        return;
      }
    }

    setSubmitting(false);
    setDialogOpen(false);
    fetchEntries();
  }

  /**
   * Toggle an entry's active status.
   *
   * @param entry - The entry to toggle.
   */
  async function handleToggleActive(entry: KnowledgeEntry): Promise<void> {
    const { error: apiError } = await api.patch<KnowledgeEntry>(
      `/api/v1/knowledge/${entry.id}`,
      { is_active: !entry.is_active }
    );
    if (apiError) {
      setError(apiError.message);
      return;
    }
    fetchEntries();
  }

  /**
   * Delete a knowledge base entry.
   *
   * @param id - The entry UUID.
   */
  async function handleDelete(id: string): Promise<void> {
    setDeleting(true);
    const { error: apiError } = await api.del(`/api/v1/knowledge/${id}`);
    setDeleting(false);
    if (apiError) {
      setError(apiError.message);
      return;
    }
    setDeleteTarget(null);
    fetchEntries();
  }

  /**
   * Get the chatbot name by its ID for display purposes.
   *
   * @param chatbotId - The chatbot UUID.
   * @returns The chatbot name or a truncated ID fallback.
   */
  function getChatbotName(chatbotId: string): string {
    const bot = chatbots.find((b) => b.id === chatbotId);
    return bot?.name || chatbotId.slice(0, 8);
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
      <PageTransition className="p-6 space-y-6">
        {/* -- Page Header -- */}
        <FadeIn direction="down">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight">
                Knowledge Base
              </h2>
              <p className="text-muted-foreground mt-1">
                Train your chatbots with product info, FAQs, and policies.
              </p>
            </div>
            <Button
              onClick={handleOpenCreate}
              disabled={chatbots.length === 0}
            >
              <Plus className="size-4" />
              Add Entry
            </Button>
          </div>
        </FadeIn>

        {/* -- Filter Bar -- */}
        <FadeIn delay={0.1}>
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-sm text-muted-foreground">Chatbot:</span>
            <select
              value={filterChatbot}
              onChange={(e) => setFilterChatbot(e.target.value)}
              className="rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">All Chatbots</option>
              {chatbots.map((bot) => (
                <option key={bot.id} value={bot.id}>
                  {bot.name}
                </option>
              ))}
            </select>
            <span className="text-sm text-muted-foreground ml-auto">
              {total} entr{total !== 1 ? "ies" : "y"}
            </span>
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

        {/* -- No Chatbots Warning -- */}
        {!loading && chatbots.length === 0 && (
          <FadeIn>
            <Card className="border-amber-500/30 bg-amber-50 dark:bg-amber-950/20">
              <CardContent className="pt-6 text-center">
                <p className="text-sm text-amber-800 dark:text-amber-200">
                  You need to create a chatbot before adding knowledge base
                  entries.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  asChild
                >
                  <a href="/chatbots">Go to Chatbots</a>
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        )}

        {/* -- Entries List -- */}
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i} className="py-4">
                <CardContent className="flex items-start gap-4">
                  <Skeleton className="size-10 rounded-lg" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-40" />
                    <Skeleton className="h-3 w-full" />
                    <Skeleton className="h-3 w-2/3" />
                  </div>
                  <Skeleton className="h-8 w-16" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : entries.length === 0 && chatbots.length > 0 ? (
          <FadeIn>
            <Card>
              <CardContent className="py-12 text-center">
                <div className="mx-auto size-14 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                  <BookOpen className="size-7 text-primary" />
                </div>
                <h3 className="font-heading font-semibold text-lg">
                  No knowledge base entries
                </h3>
                <p className="text-muted-foreground text-sm mt-1 max-w-md mx-auto">
                  Add product information, FAQs, and policies so your chatbot
                  can give accurate, helpful responses to customer questions.
                </p>
                <Button className="mt-5" onClick={handleOpenCreate}>
                  <Plus className="size-4" />
                  Add your first entry
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        ) : (
          <StaggerChildren className="space-y-3" staggerDelay={0.05}>
            {entries.map((entry) => {
              const SourceIcon = getSourceIcon(entry.source_type);

              return (
                <Card key={entry.id} className="py-4">
                  <CardContent className="flex items-start gap-4">
                    {/* Source Type Icon */}
                    <div
                      className={`size-10 rounded-lg flex items-center justify-center shrink-0 ${
                        entry.is_active
                          ? "bg-primary/10"
                          : "bg-muted"
                      }`}
                    >
                      <SourceIcon
                        className={`size-5 ${
                          entry.is_active
                            ? "text-primary"
                            : "text-muted-foreground"
                        }`}
                      />
                    </div>

                    {/* Entry Details */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p
                          className={`font-medium truncate ${
                            !entry.is_active ? "text-muted-foreground" : ""
                          }`}
                        >
                          {entry.title}
                        </p>
                        <Badge
                          variant="outline"
                          className="text-[10px] px-1.5"
                        >
                          {getSourceLabel(entry.source_type)}
                        </Badge>
                        {!entry.is_active && (
                          <Badge
                            variant="secondary"
                            className="text-[10px] px-1.5"
                          >
                            Inactive
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                        {entry.content}
                      </p>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground mt-2">
                        <span>{getChatbotName(entry.chatbot_id)}</span>
                        <span>Updated {formatDate(entry.updated_at)}</span>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1 shrink-0">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-8"
                        onClick={() => handleToggleActive(entry)}
                        title={
                          entry.is_active ? "Deactivate" : "Activate"
                        }
                      >
                        {entry.is_active ? (
                          <ToggleRight className="size-4 text-emerald-600" />
                        ) : (
                          <ToggleLeft className="size-4 text-muted-foreground" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-8"
                        onClick={() => handleOpenEdit(entry)}
                      >
                        <Pencil className="size-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-8 text-muted-foreground hover:text-destructive"
                        onClick={() => setDeleteTarget(entry)}
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </StaggerChildren>
        )}

        {/* -- Create/Edit Dialog -- */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>
                {editing ? "Edit Entry" : "Add Knowledge Entry"}
              </DialogTitle>
              <DialogDescription>
                {editing
                  ? "Update the content your chatbot uses to answer questions."
                  : "Add information your chatbot can reference when answering customer questions."}
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2">
              {/* Chatbot Selector (only for create) */}
              {!editing && (
                <div className="space-y-2">
                  <label className="text-sm font-medium">Chatbot</label>
                  <select
                    value={formChatbotId}
                    onChange={(e) => setFormChatbotId(e.target.value)}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  >
                    {chatbots.map((bot) => (
                      <option key={bot.id} value={bot.id}>
                        {bot.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Source Type */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Type</label>
                <div className="flex flex-wrap gap-2">
                  {SOURCE_TYPES.map((st) => {
                    const Icon = st.icon;
                    return (
                      <button
                        key={st.value}
                        type="button"
                        onClick={() => setFormSourceType(st.value)}
                        className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm transition-colors ${
                          formSourceType === st.value
                            ? "border-primary bg-primary/10 text-primary font-medium"
                            : "border-input hover:bg-secondary text-muted-foreground"
                        }`}
                      >
                        <Icon className="size-3.5" />
                        {st.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Title */}
              <div className="space-y-2">
                <label htmlFor="entry-title" className="text-sm font-medium">
                  Title
                </label>
                <Input
                  id="entry-title"
                  placeholder="e.g. Return Policy, FAQ: Shipping"
                  value={formTitle}
                  onChange={(e) => setFormTitle(e.target.value)}
                />
              </div>

              {/* Content */}
              <div className="space-y-2">
                <label htmlFor="entry-content" className="text-sm font-medium">
                  Content
                </label>
                <textarea
                  id="entry-content"
                  placeholder="Enter the full text content your chatbot should reference..."
                  value={formContent}
                  onChange={(e) => setFormContent(e.target.value)}
                  rows={5}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 resize-y min-h-[100px]"
                />
                <p className="text-xs text-muted-foreground">
                  The more detailed and accurate the content, the better your
                  chatbot's responses will be.
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
                    : "Adding..."
                  : editing
                    ? "Save Changes"
                    : "Add Entry"}
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
              <DialogTitle>Delete Entry</DialogTitle>
              <DialogDescription>
                Are you sure you want to delete{" "}
                <strong>&quot;{deleteTarget?.title}&quot;</strong>? Your
                chatbot will no longer be able to reference this content
                when answering questions.
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
                {deleting ? "Deleting..." : "Delete Entry"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageTransition>
    </Shell>
  );
}
