/**
 * Template management page — create, edit, and delete content templates.
 *
 * Displays system templates (read-only) and the user's custom templates
 * in a card grid. Users can create new templates, edit their custom ones,
 * and delete those they no longer need. System templates are visually
 * distinguished with a "System" badge and cannot be modified.
 *
 * **For Developers:**
 *   - Fetches from `GET /api/v1/templates/` on mount.
 *   - Creates templates via `POST /api/v1/templates/` with name, tone, style, etc.
 *   - Updates templates via `PATCH /api/v1/templates/{id}` with partial data.
 *   - Deletes templates via `DELETE /api/v1/templates/{id}`.
 *   - Uses Shell wrapper, motion animations, Dialog for create/edit forms.
 *   - System templates have `is_system=true` and show a lock indicator.
 *
 * **For Project Managers:**
 *   - Templates are a key feature for personalizing AI output to a brand voice.
 *   - System templates provide ready-made options for quick starts.
 *   - Custom templates increase stickiness — users invest in configuring them.
 *
 * **For QA Engineers:**
 *   - Verify system templates appear with a "System" badge and no edit/delete buttons.
 *   - Verify custom templates can be created, edited, and deleted.
 *   - Test the create dialog with all fields filled and with minimal fields.
 *   - Verify editing preserves unchanged fields.
 *   - Test with no templates (empty state).
 *   - Verify tone and style selectors show correct options.
 *
 * **For End Users:**
 *   - Templates control the tone and style of your generated content.
 *   - System templates are ready to use. Create custom templates for your brand.
 *   - Click a template card to see its details, or use the edit button to modify it.
 */

"use client";

import * as React from "react";
import {
  FileText,
  Plus,
  Pencil,
  Trash2,
  Loader2,
  Lock,
  AlertCircle,
  Mic2,
  LayoutList,
  Sparkles,
} from "lucide-react";
import { Shell } from "@/components/shell";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { FadeIn, StaggerChildren, PageTransition } from "@/components/motion";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

/* ── Type Definitions ─────────────────────────────────────────────── */

/** Shape of a template from the API. */
interface Template {
  id: string;
  user_id: string | null;
  name: string;
  description: string | null;
  tone: string;
  style: string;
  prompt_override: string | null;
  content_types: string[];
  is_default: boolean;
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

/** Tone options for the template form selector. */
const TONE_OPTIONS = [
  { value: "professional", label: "Professional", icon: "briefcase" },
  { value: "casual", label: "Casual", icon: "coffee" },
  { value: "luxury", label: "Luxury", icon: "gem" },
  { value: "playful", label: "Playful", icon: "smile" },
  { value: "technical", label: "Technical", icon: "cpu" },
] as const;

/** Style options for the template form selector. */
const STYLE_OPTIONS = [
  { value: "concise", label: "Concise" },
  { value: "detailed", label: "Detailed" },
  { value: "storytelling", label: "Storytelling" },
  { value: "list-based", label: "List-based" },
] as const;

/** Available content types for template configuration. */
const CONTENT_TYPES = [
  { key: "title", label: "Title" },
  { key: "description", label: "Description" },
  { key: "meta_description", label: "Meta Description" },
  { key: "keywords", label: "Keywords" },
  { key: "bullet_points", label: "Bullet Points" },
] as const;

/* ── Main Component ───────────────────────────────────────────────── */

/**
 * Template management page component.
 *
 * Renders a grid of system and custom templates with create/edit/delete
 * functionality via dialog forms.
 *
 * @returns The templates page wrapped in the Shell layout.
 */
export default function TemplatesPage() {
  /* ── State ── */
  const [templates, setTemplates] = React.useState<Template[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [deletingId, setDeletingId] = React.useState<string | null>(null);

  /* Dialog state for create/edit */
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editingTemplate, setEditingTemplate] = React.useState<Template | null>(null);
  const [formName, setFormName] = React.useState("");
  const [formDescription, setFormDescription] = React.useState("");
  const [formTone, setFormTone] = React.useState("professional");
  const [formStyle, setFormStyle] = React.useState("detailed");
  const [formPromptOverride, setFormPromptOverride] = React.useState("");
  const [formContentTypes, setFormContentTypes] = React.useState<string[]>(
    CONTENT_TYPES.map((t) => t.key)
  );
  const [saving, setSaving] = React.useState(false);

  /* ── Data Fetching ── */

  /**
   * Fetch all templates (system + custom) from the API.
   * Updates templates, loading, and error state.
   */
  const fetchTemplates = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    const { data, error: apiError } = await api.get<Template[]>(
      "/api/v1/templates/"
    );
    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setTemplates(data);
    }
    setLoading(false);
  }, []);

  React.useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  /* ── Actions ── */

  /**
   * Open the create dialog with a blank form.
   */
  function handleOpenCreate() {
    setEditingTemplate(null);
    setFormName("");
    setFormDescription("");
    setFormTone("professional");
    setFormStyle("detailed");
    setFormPromptOverride("");
    setFormContentTypes(CONTENT_TYPES.map((t) => t.key));
    setDialogOpen(true);
  }

  /**
   * Open the edit dialog pre-filled with the template's current values.
   *
   * @param tpl - The template to edit.
   */
  function handleOpenEdit(tpl: Template) {
    setEditingTemplate(tpl);
    setFormName(tpl.name);
    setFormDescription(tpl.description || "");
    setFormTone(tpl.tone);
    setFormStyle(tpl.style);
    setFormPromptOverride(tpl.prompt_override || "");
    setFormContentTypes(tpl.content_types);
    setDialogOpen(true);
  }

  /**
   * Save the template (create or update) based on whether editingTemplate is set.
   * On success, closes the dialog and refreshes the list.
   */
  async function handleSave() {
    if (!formName.trim()) return;
    setSaving(true);
    setError(null);

    const body: Record<string, unknown> = {
      name: formName.trim(),
      description: formDescription.trim() || null,
      tone: formTone,
      style: formStyle,
      prompt_override: formPromptOverride.trim() || null,
      content_types: formContentTypes,
    };

    let apiError;
    if (editingTemplate) {
      /* Update existing template */
      const result = await api.patch<Template>(
        `/api/v1/templates/${editingTemplate.id}`,
        body
      );
      apiError = result.error;
    } else {
      /* Create new template */
      const result = await api.post<Template>("/api/v1/templates/", body);
      apiError = result.error;
    }

    setSaving(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    setDialogOpen(false);
    fetchTemplates();
  }

  /**
   * Delete a custom template by ID.
   * On success, refreshes the template list.
   *
   * @param templateId - The UUID of the template to delete.
   */
  async function handleDelete(templateId: string) {
    setDeletingId(templateId);
    const { error: apiError } = await api.del(
      `/api/v1/templates/${templateId}`
    );
    setDeletingId(null);
    if (apiError) {
      setError(apiError.message);
      return;
    }
    fetchTemplates();
  }

  /**
   * Toggle a content type in the form's selected types list.
   *
   * @param typeKey - The content type key to toggle.
   */
  function toggleContentType(typeKey: string) {
    setFormContentTypes((prev) =>
      prev.includes(typeKey)
        ? prev.filter((t) => t !== typeKey)
        : [...prev, typeKey]
    );
  }

  /* ── Derived data ── */
  const systemTemplates = templates.filter((t) => t.is_system);
  const customTemplates = templates.filter((t) => !t.is_system);

  /* ── Render ── */
  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* ── Page Header ── */}
        <FadeIn direction="down">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight">
                Content Templates
              </h2>
              <p className="text-muted-foreground mt-1">
                Manage templates that control the tone and style of generated content.
              </p>
            </div>
            <Button onClick={handleOpenCreate}>
              <Plus className="size-4" />
              New Template
            </Button>
          </div>
        </FadeIn>

        {/* ── Loading Skeletons ── */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-5 w-32" />
                  <Skeleton className="h-4 w-48 mt-1" />
                </CardHeader>
                <CardContent className="space-y-2">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-4 w-20" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : error && templates.length === 0 ? (
          /* ── Error State ── */
          <FadeIn>
            <Card className="border-destructive/50">
              <CardContent className="pt-6 flex items-start gap-3">
                <AlertCircle className="size-5 text-destructive shrink-0 mt-0.5" />
                <div>
                  <p className="text-destructive text-sm font-medium">
                    Failed to load templates
                  </p>
                  <p className="text-destructive/80 text-sm mt-1">{error}</p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-3"
                    onClick={() => fetchTemplates()}
                  >
                    Retry
                  </Button>
                </div>
              </CardContent>
            </Card>
          </FadeIn>
        ) : (
          <>
            {/* ── System Templates ── */}
            {systemTemplates.length > 0 && (
              <div>
                <FadeIn>
                  <h3 className="font-heading text-lg font-semibold mb-4 flex items-center gap-2">
                    <Lock className="size-4 text-muted-foreground" />
                    System Templates
                  </h3>
                </FadeIn>
                <StaggerChildren
                  className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
                  staggerDelay={0.06}
                >
                  {systemTemplates.map((tpl) => (
                    <TemplateCard
                      key={tpl.id}
                      template={tpl}
                      onEdit={() => {}}
                      onDelete={() => {}}
                      deleting={false}
                      isSystem
                    />
                  ))}
                </StaggerChildren>
              </div>
            )}

            {/* ── Custom Templates ── */}
            <div>
              <FadeIn delay={systemTemplates.length > 0 ? 0.2 : 0}>
                <h3 className="font-heading text-lg font-semibold mb-4 flex items-center gap-2">
                  <Sparkles className="size-4 text-muted-foreground" />
                  Your Templates
                </h3>
              </FadeIn>
              {customTemplates.length === 0 ? (
                <FadeIn delay={0.1}>
                  <Card>
                    <CardContent className="pt-6 text-center py-12">
                      <FileText className="size-10 text-muted-foreground/40 mx-auto mb-3" />
                      <h4 className="font-heading font-semibold">
                        No custom templates yet
                      </h4>
                      <p className="text-muted-foreground text-sm mt-1 max-w-sm mx-auto">
                        Create a template to save your preferred tone and style
                        for consistent content generation.
                      </p>
                      <Button
                        className="mt-4"
                        size="sm"
                        onClick={handleOpenCreate}
                      >
                        <Plus className="size-4" />
                        Create Template
                      </Button>
                    </CardContent>
                  </Card>
                </FadeIn>
              ) : (
                <StaggerChildren
                  className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
                  staggerDelay={0.06}
                >
                  {customTemplates.map((tpl) => (
                    <TemplateCard
                      key={tpl.id}
                      template={tpl}
                      onEdit={() => handleOpenEdit(tpl)}
                      onDelete={() => handleDelete(tpl.id)}
                      deleting={deletingId === tpl.id}
                      isSystem={false}
                    />
                  ))}
                </StaggerChildren>
              )}
            </div>
          </>
        )}

        {/* ── Inline Error Toast ── */}
        {error && templates.length > 0 && (
          <FadeIn>
            <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          </FadeIn>
        )}

        {/* ── Create / Edit Dialog ── */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="font-heading">
                {editingTemplate ? "Edit Template" : "New Template"}
              </DialogTitle>
              <DialogDescription>
                {editingTemplate
                  ? "Update your template settings."
                  : "Create a custom template to control AI content style."}
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2">
              {/* Name */}
              <div className="space-y-1.5">
                <label htmlFor="tpl-name" className="text-sm font-medium">
                  Template Name <span className="text-destructive">*</span>
                </label>
                <Input
                  id="tpl-name"
                  placeholder="e.g. Luxury Brand Voice"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                />
              </div>

              {/* Description */}
              <div className="space-y-1.5">
                <label htmlFor="tpl-desc" className="text-sm font-medium">
                  Description
                </label>
                <Input
                  id="tpl-desc"
                  placeholder="Brief description of this template's purpose"
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                />
              </div>

              {/* Tone Selector */}
              <div className="space-y-2">
                <span className="text-sm font-medium flex items-center gap-1.5">
                  <Mic2 className="size-3.5" />
                  Tone
                </span>
                <div className="flex flex-wrap gap-2">
                  {TONE_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => setFormTone(opt.value)}
                      className={cn(
                        "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                        formTone === opt.value
                          ? "bg-primary text-primary-foreground border-primary"
                          : "bg-background text-muted-foreground border-input hover:bg-secondary"
                      )}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Style Selector */}
              <div className="space-y-2">
                <span className="text-sm font-medium flex items-center gap-1.5">
                  <LayoutList className="size-3.5" />
                  Style
                </span>
                <div className="flex flex-wrap gap-2">
                  {STYLE_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => setFormStyle(opt.value)}
                      className={cn(
                        "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                        formStyle === opt.value
                          ? "bg-primary text-primary-foreground border-primary"
                          : "bg-background text-muted-foreground border-input hover:bg-secondary"
                      )}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Content Types */}
              <div className="space-y-2">
                <span className="text-sm font-medium">Content Types</span>
                <div className="flex flex-wrap gap-2">
                  {CONTENT_TYPES.map((ct) => {
                    const isSelected = formContentTypes.includes(ct.key);
                    return (
                      <button
                        key={ct.key}
                        type="button"
                        onClick={() => toggleContentType(ct.key)}
                        className={cn(
                          "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                          isSelected
                            ? "bg-primary text-primary-foreground border-primary"
                            : "bg-background text-muted-foreground border-input hover:bg-secondary"
                        )}
                      >
                        {ct.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Prompt Override (advanced) */}
              <div className="space-y-1.5">
                <label htmlFor="tpl-prompt" className="text-sm font-medium">
                  Custom Prompt
                  <span className="text-muted-foreground font-normal ml-1">(advanced)</span>
                </label>
                <Input
                  id="tpl-prompt"
                  placeholder="Override the default AI prompt..."
                  value={formPromptOverride}
                  onChange={(e) => setFormPromptOverride(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  If set, this completely replaces the default generation prompt.
                </p>
              </div>
            </div>

            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setDialogOpen(false)}
                disabled={saving}
              >
                Cancel
              </Button>
              <Button
                onClick={handleSave}
                disabled={saving || !formName.trim() || formContentTypes.length === 0}
              >
                {saving ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : editingTemplate ? (
                  <Pencil className="size-4" />
                ) : (
                  <Plus className="size-4" />
                )}
                {editingTemplate ? "Save Changes" : "Create Template"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageTransition>
    </Shell>
  );
}

/* ── Template Card Sub-Component ──────────────────────────────────── */

/** Props for the TemplateCard sub-component. */
interface TemplateCardProps {
  /** The template data to render. */
  template: Template;
  /** Callback when the edit button is clicked. */
  onEdit: () => void;
  /** Callback when the delete button is clicked. */
  onDelete: () => void;
  /** Whether this card's delete action is currently in progress. */
  deleting: boolean;
  /** Whether this is a system (read-only) template. */
  isSystem: boolean;
}

/**
 * Individual template card rendering name, tone, style, content types,
 * and edit/delete actions for custom templates.
 *
 * @param props - TemplateCardProps.
 * @returns A Card component displaying the template details.
 */
function TemplateCard({
  template,
  onEdit,
  onDelete,
  deleting,
  isSystem,
}: TemplateCardProps) {
  return (
    <Card
      className={cn(
        "flex flex-col transition-shadow hover:shadow-md",
        isSystem && "border-dashed opacity-90"
      )}
    >
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="font-heading text-base">
            {template.name}
          </CardTitle>
          <div className="flex items-center gap-1.5 shrink-0">
            {isSystem && (
              <Badge variant="secondary" className="text-xs">
                <Lock className="size-3 mr-1" />
                System
              </Badge>
            )}
            {template.is_default && (
              <Badge variant="default" className="text-xs">
                Default
              </Badge>
            )}
          </div>
        </div>
        {template.description && (
          <CardDescription className="line-clamp-2">
            {template.description}
          </CardDescription>
        )}
      </CardHeader>

      <CardContent className="flex-1 space-y-3">
        {/* Tone and Style */}
        <div className="flex items-center gap-3 text-sm">
          <span className="flex items-center gap-1 text-muted-foreground">
            <Mic2 className="size-3.5" />
            <span className="capitalize">{template.tone}</span>
          </span>
          <span className="text-muted-foreground/30">|</span>
          <span className="flex items-center gap-1 text-muted-foreground">
            <LayoutList className="size-3.5" />
            <span className="capitalize">{template.style}</span>
          </span>
        </div>

        {/* Content Types Chips */}
        <div className="flex flex-wrap gap-1.5">
          {template.content_types.map((ct) => (
            <Badge key={ct} variant="outline" className="text-xs capitalize">
              {ct.replace("_", " ")}
            </Badge>
          ))}
        </div>

        {/* Prompt override indicator */}
        {template.prompt_override && (
          <p className="text-xs text-muted-foreground italic truncate">
            Custom prompt: {template.prompt_override}
          </p>
        )}
      </CardContent>

      {!isSystem && (
        <CardFooter className="gap-2">
          <Button variant="outline" size="sm" className="flex-1" onClick={onEdit}>
            <Pencil className="size-3.5" />
            Edit
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="text-destructive hover:text-destructive hover:bg-destructive/10"
            onClick={onDelete}
            disabled={deleting}
          >
            {deleting ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <Trash2 className="size-3.5" />
            )}
          </Button>
        </CardFooter>
      )}
    </Card>
  );
}
