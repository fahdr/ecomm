/**
 * SMS Templates page — create, edit, and manage reusable SMS message templates.
 *
 * Displays a grid/list of SMS templates with name, category, body preview,
 * and actions (edit, delete). Includes create/edit dialogs with character
 * counting and delete confirmation.
 *
 * **For Developers:**
 *   - `GET /api/v1/sms/templates` — list all SMS templates.
 *   - `POST /api/v1/sms/templates` — create a new template.
 *   - `PATCH /api/v1/sms/templates/:id` — update an existing template.
 *   - `DELETE /api/v1/sms/templates/:id` — delete a template (204 No Content).
 *   - Templates have a 1600 character limit matching the SMS campaign body limit.
 *   - Category is a free-text field for organizational grouping.
 *
 * **For Project Managers:**
 *   - Templates reduce repetitive work for merchants sending similar SMS messages.
 *   - Categories help organize templates (e.g. "promotions", "transactional", "alerts").
 *   - Template management is a secondary feature supporting the core SMS campaign flow.
 *
 * **For QA Engineers:**
 *   - Test with 0 templates (empty state) and with multiple templates.
 *   - Verify create dialog: name required, body required, body <= 1600 chars.
 *   - Verify edit dialog pre-fills with existing template data.
 *   - Verify delete confirmation dialog and that deletion removes the template from the list.
 *   - Test character counter in both create and edit dialogs.
 *   - Verify toast notifications appear for create, edit, and delete actions.
 *
 * **For End Users:**
 *   - Save frequently used SMS messages as templates for quick reuse.
 *   - Organize templates by category for easy filtering.
 *   - Edit or delete templates at any time.
 */

"use client";

import * as React from "react";
import {
  MessageSquareText,
  Plus,
  Pencil,
  Trash2,
  Loader2,
  Tag,
  Clock,
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
  AnimatedCounter,
  PageTransition,
} from "@/components/motion";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

/** Maximum character count for an SMS template body. */
const MAX_BODY_LENGTH = 1600;

/** Shape of an SMS template as returned by the API. */
interface SmsTemplate {
  id: string;
  name: string;
  body: string;
  category: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * SMS Templates page component.
 *
 * Manages the list of SMS templates with create, edit, and delete
 * functionality via modal dialogs. Includes empty state, loading state,
 * and toast notifications.
 *
 * @returns The SMS templates management page wrapped in the Shell layout.
 */
export default function SmsTemplatesPage() {
  /* ── List state ── */
  const [templates, setTemplates] = React.useState<SmsTemplate[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  /* ── Create/Edit dialog state ── */
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editTarget, setEditTarget] = React.useState<SmsTemplate | null>(null);
  const [formName, setFormName] = React.useState("");
  const [formBody, setFormBody] = React.useState("");
  const [formCategory, setFormCategory] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);

  /* ── Delete dialog state ── */
  const [deleteTarget, setDeleteTarget] = React.useState<SmsTemplate | null>(null);
  const [deleting, setDeleting] = React.useState(false);

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
   * Fetch all SMS templates from the API.
   */
  async function fetchTemplates() {
    setLoading(true);
    setError(null);

    const { data, error: apiError } = await api.get<SmsTemplate[] | { items: SmsTemplate[] }>(
      "/api/v1/sms/templates"
    );
    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      /* Handle both array and paginated response shapes */
      const items = Array.isArray(data) ? data : data.items;
      setTemplates(items);
    }
    setLoading(false);
  }

  /** Fetch on mount. */
  React.useEffect(() => {
    fetchTemplates();
  }, []);

  /** Remaining character count for the body text. */
  const charsRemaining = MAX_BODY_LENGTH - formBody.length;

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
   * Open the create dialog with empty fields.
   */
  function openCreateDialog() {
    setEditTarget(null);
    setFormName("");
    setFormBody("");
    setFormCategory("");
    setDialogOpen(true);
  }

  /**
   * Open the edit dialog pre-filled with the selected template's data.
   *
   * @param template - The template to edit.
   */
  function openEditDialog(template: SmsTemplate) {
    setEditTarget(template);
    setFormName(template.name);
    setFormBody(template.body);
    setFormCategory(template.category || "");
    setDialogOpen(true);
  }

  /**
   * Submit the create or edit form to the API.
   * Creates a new template if no editTarget, otherwise updates the existing one.
   */
  async function handleSubmit() {
    if (!formName.trim()) {
      setError("Template name is required.");
      return;
    }
    if (!formBody.trim()) {
      setError("Template body is required.");
      return;
    }
    if (formBody.length > MAX_BODY_LENGTH) {
      setError(`Template body cannot exceed ${MAX_BODY_LENGTH} characters.`);
      return;
    }

    setSubmitting(true);
    setError(null);

    const payload = {
      name: formName.trim(),
      body: formBody.trim(),
      category: formCategory.trim() || null,
    };

    if (editTarget) {
      /* Update existing template */
      const { error: apiError } = await api.patch(
        `/api/v1/sms/templates/${editTarget.id}`,
        payload
      );
      setSubmitting(false);

      if (apiError) {
        setError(apiError.message);
        showToast(apiError.message, "error");
        return;
      }

      showToast("Template updated successfully!", "success");
    } else {
      /* Create new template */
      const { error: apiError } = await api.post(
        "/api/v1/sms/templates",
        payload
      );
      setSubmitting(false);

      if (apiError) {
        setError(apiError.message);
        showToast(apiError.message, "error");
        return;
      }

      showToast("Template created successfully!", "success");
    }

    setDialogOpen(false);
    setEditTarget(null);
    fetchTemplates();
  }

  /**
   * Delete a template after user confirmation.
   *
   * @param id - The template UUID.
   */
  async function handleDelete(id: string) {
    setDeleting(true);
    const { error: apiError } = await api.del(`/api/v1/sms/templates/${id}`);
    setDeleting(false);

    if (apiError) {
      setError(apiError.message);
      showToast(apiError.message, "error");
      return;
    }

    setDeleteTarget(null);
    showToast("Template deleted.", "success");
    fetchTemplates();
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

  /** Get unique categories from the templates list. */
  const categories = Array.from(
    new Set(templates.map((t) => t.category).filter(Boolean))
  ) as string[];

  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* ── Page Header ── */}
        <FadeIn direction="down">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight">
                SMS Templates
              </h2>
              <p className="text-muted-foreground mt-1">
                Create reusable SMS message templates for your campaigns.
              </p>
            </div>
            <Button
              onClick={openCreateDialog}
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              <Plus className="size-4" />
              New Template
            </Button>
          </div>
        </FadeIn>

        {/* ── KPI Card ── */}
        <FadeIn delay={0.08}>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Total Templates
                </CardTitle>
                <MessageSquareText className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <AnimatedCounter
                  value={templates.length}
                  className="text-3xl font-bold font-heading"
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Categories
                </CardTitle>
                <Tag className="size-4 text-emerald-500" />
              </CardHeader>
              <CardContent>
                <AnimatedCounter
                  value={categories.length}
                  className="text-3xl font-bold font-heading text-emerald-600 dark:text-emerald-400"
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Last Updated
                </CardTitle>
                <Clock className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <p className="text-sm font-medium font-heading">
                  {templates.length > 0
                    ? formatDate(
                        templates.reduce((latest, t) =>
                          t.updated_at > latest.updated_at ? t : latest
                        ).updated_at
                      )
                    : "--"}
                </p>
              </CardContent>
            </Card>
          </div>
        </FadeIn>

        {/* ── Templates Grid ── */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Card key={i}>
                <CardContent className="pt-6 space-y-3">
                  <Skeleton className="h-5 w-32" />
                  <Skeleton className="h-3 w-16" />
                  <Skeleton className="h-16 w-full" />
                  <Skeleton className="h-3 w-24" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : templates.length === 0 ? (
          <FadeIn>
            <Card>
              <CardContent className="pt-12 pb-12 text-center">
                <div className="mx-auto size-12 rounded-full bg-emerald-100 dark:bg-emerald-900/20 flex items-center justify-center mb-4">
                  <MessageSquareText className="size-6 text-emerald-600 dark:text-emerald-400" />
                </div>
                <h3 className="font-heading font-semibold text-lg">
                  No SMS templates yet
                </h3>
                <p className="text-muted-foreground text-sm mt-1 max-w-sm mx-auto">
                  Create reusable message templates to speed up your SMS
                  campaign creation workflow.
                </p>
                <Button
                  className="mt-4 bg-emerald-600 hover:bg-emerald-700 text-white"
                  onClick={openCreateDialog}
                >
                  <Plus className="size-4" />
                  Create your first template
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        ) : (
          <StaggerChildren
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
            staggerDelay={0.06}
          >
            {templates.map((template) => (
              <Card key={template.id} className="group relative">
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <div className="space-y-1 min-w-0 flex-1">
                      <CardTitle className="text-base truncate">
                        {template.name}
                      </CardTitle>
                      {template.category && (
                        <Badge
                          variant="outline"
                          className="text-xs border-emerald-300 text-emerald-700 dark:border-emerald-700 dark:text-emerald-400"
                        >
                          {template.category}
                        </Badge>
                      )}
                    </div>
                    {/* Action buttons */}
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-7"
                        onClick={() => openEditDialog(template)}
                        title="Edit template"
                      >
                        <Pencil className="size-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-7 text-muted-foreground hover:text-destructive"
                        onClick={() => setDeleteTarget(template)}
                        title="Delete template"
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  {/* Body preview */}
                  <div className="rounded-md bg-muted/50 p-3 border">
                    <p className="text-sm text-muted-foreground leading-relaxed line-clamp-4">
                      {template.body}
                    </p>
                  </div>
                  {/* Metadata */}
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{template.body.length} chars</span>
                    <span>Created {formatDate(template.created_at)}</span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </StaggerChildren>
        )}

        {/* ── Error Message ── */}
        {error && !dialogOpen && (
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

        {/* ── Create / Edit Template Dialog ── */}
        <Dialog
          open={dialogOpen}
          onOpenChange={(open) => {
            if (!open) {
              setDialogOpen(false);
              setEditTarget(null);
              setError(null);
            }
          }}
        >
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle>
                {editTarget ? "Edit Template" : "New Template"}
              </DialogTitle>
              <DialogDescription>
                {editTarget
                  ? "Update the template name, body, and category."
                  : "Create a reusable SMS message template for your campaigns."}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              {/* Template Name */}
              <div className="space-y-2">
                <label htmlFor="tpl-name" className="text-sm font-medium">
                  Template Name <span className="text-destructive">*</span>
                </label>
                <Input
                  id="tpl-name"
                  placeholder="e.g. Welcome Message"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                />
              </div>

              {/* Template Body */}
              <div className="space-y-2">
                <label htmlFor="tpl-body" className="text-sm font-medium">
                  Message Body <span className="text-destructive">*</span>
                </label>
                <textarea
                  id="tpl-body"
                  rows={5}
                  maxLength={MAX_BODY_LENGTH}
                  placeholder="Type your template message..."
                  value={formBody}
                  onChange={(e) => setFormBody(e.target.value)}
                  className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background resize-y min-h-[100px]"
                />
                <div className="flex items-center justify-end">
                  <p className={cn("text-xs tabular-nums", counterColor())}>
                    {charsRemaining.toLocaleString()} / {MAX_BODY_LENGTH.toLocaleString()} remaining
                  </p>
                </div>
              </div>

              {/* Category */}
              <div className="space-y-2">
                <label htmlFor="tpl-category" className="text-sm font-medium">
                  Category{" "}
                  <span className="text-muted-foreground font-normal">(optional)</span>
                </label>
                <Input
                  id="tpl-category"
                  placeholder="e.g. promotions, alerts, transactional"
                  value={formCategory}
                  onChange={(e) => setFormCategory(e.target.value)}
                />
              </div>

              {/* Dialog-scoped error */}
              {error && dialogOpen && (
                <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3">
                  <p className="text-sm text-destructive">{error}</p>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => {
                  setDialogOpen(false);
                  setEditTarget(null);
                  setError(null);
                }}
                disabled={submitting}
              >
                Cancel
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={submitting}
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
              >
                {submitting && <Loader2 className="size-4 animate-spin" />}
                {submitting
                  ? editTarget
                    ? "Saving..."
                    : "Creating..."
                  : editTarget
                    ? "Save Changes"
                    : "Create Template"}
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
              <DialogTitle>Delete Template</DialogTitle>
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
                {deleting ? "Deleting..." : "Delete Template"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageTransition>
    </Shell>
  );
}
