/**
 * Flows page — create, manage, and monitor automated email sequences.
 *
 * Displays a filterable, paginated list of automation flows with status
 * badges, step counts, trigger types, and lifecycle action buttons.
 * Includes dialogs for creating flows, editing draft/paused flows,
 * activating, pausing, and deleting flows.
 *
 * **For Developers:**
 *   - `GET /api/v1/flows?page=&page_size=&status=` — paginated flow list.
 *   - `POST /api/v1/flows` — create a flow (starts as draft).
 *   - `PATCH /api/v1/flows/:id` — update a draft or paused flow.
 *   - `DELETE /api/v1/flows/:id` — delete a flow.
 *   - `POST /api/v1/flows/:id/activate` — activate (requires steps).
 *   - `POST /api/v1/flows/:id/pause` — pause an active flow.
 *   - Status lifecycle: draft -> active -> paused -> active (re-activate).
 *   - Active flows cannot be edited — must be paused first.
 *
 * **For Project Managers:**
 *   - Flows are the core automation feature. They reduce manual work
 *     and improve engagement through timely automated email sequences.
 *   - The lifecycle model (draft/active/paused) prevents accidental
 *     modifications to running automations.
 *
 * **For QA Engineers:**
 *   - Test with 0 flows (empty state), draft, active, and paused flows.
 *   - Verify status filter shows only matching flows.
 *   - Verify draft flows show Edit/Activate/Delete; active flows show Pause.
 *   - Test activation fails for flows with no steps (400 error).
 *   - Test pausing a draft flow fails (400 error).
 *   - Test that active flows cannot be edited (buttons hidden or disabled).
 *   - Verify the flow step editor in the create dialog.
 *
 * **For End Users:**
 *   - Create automated email sequences that trigger on events like
 *     new signups or purchases.
 *   - Build your flow steps, then activate to start processing triggers.
 *   - Pause a flow at any time to stop processing without losing it.
 */

"use client";

import * as React from "react";
import {
  GitBranch,
  Plus,
  Play,
  Pause,
  Trash2,
  Pencil,
  Loader2,
  Zap,
  ChevronLeft,
  ChevronRight,
  Clock,
  CheckCircle2,
  CircleDot,
  AlertCircle,
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

/** Shape of a flow as returned by the API. */
interface Flow {
  id: string;
  name: string;
  description: string | null;
  trigger_type: string;
  trigger_config: Record<string, unknown>;
  status: string;
  steps: Record<string, unknown>[] | Record<string, unknown>;
  stats: Record<string, unknown>;
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

/** Status filter options for the flow list. */
const STATUS_FILTERS = [
  { label: "All", value: "" },
  { label: "Draft", value: "draft" },
  { label: "Active", value: "active" },
  { label: "Paused", value: "paused" },
];

/** Valid trigger type options for the create/edit dialogs. */
const TRIGGER_TYPES = [
  { label: "New Signup", value: "signup" },
  { label: "Purchase", value: "purchase" },
  { label: "Abandoned Cart", value: "abandoned_cart" },
  { label: "Scheduled", value: "scheduled" },
  { label: "Custom Event", value: "custom" },
];

/**
 * Map a flow status string to a Badge variant.
 *
 * @param status - The flow status string (draft, active, paused).
 * @returns The appropriate badge variant.
 */
function statusVariant(
  status: string
): "default" | "secondary" | "success" | "destructive" | "outline" {
  switch (status) {
    case "active":
      return "success";
    case "paused":
      return "destructive";
    case "draft":
      return "secondary";
    default:
      return "outline";
  }
}

/**
 * Get the icon component for a flow status.
 *
 * @param props - Object with the status string.
 * @returns A React element for the status icon.
 */
function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case "active":
      return <CheckCircle2 className="size-3.5 text-emerald-500" />;
    case "paused":
      return <Pause className="size-3.5 text-red-500" />;
    case "draft":
      return <CircleDot className="size-3.5 text-amber-500" />;
    default:
      return <Clock className="size-3.5" />;
  }
}

/**
 * Get a human-readable label for a trigger type.
 *
 * @param triggerType - The trigger type string.
 * @returns A human-readable label.
 */
function getTriggerLabel(triggerType: string): string {
  const found = TRIGGER_TYPES.find((t) => t.value === triggerType);
  return found ? found.label : triggerType;
}

/**
 * Count the steps in a flow's steps field (handles both array and object).
 *
 * @param steps - The flow steps (array or object).
 * @returns The number of steps.
 */
function countSteps(
  steps: Record<string, unknown>[] | Record<string, unknown>
): number {
  if (Array.isArray(steps)) return steps.length;
  return 0;
}

/**
 * Flows page component.
 *
 * @returns The flows management page wrapped in the Shell layout.
 */
export default function FlowsPage() {
  /* ── List state ── */
  const [flows, setFlows] = React.useState<Flow[]>([]);
  const [totalFlows, setTotalFlows] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [pageSize] = React.useState(20);
  const [statusFilter, setStatusFilter] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  /* ── Create dialog state ── */
  const [createOpen, setCreateOpen] = React.useState(false);
  const [newName, setNewName] = React.useState("");
  const [newDescription, setNewDescription] = React.useState("");
  const [newTriggerType, setNewTriggerType] = React.useState("signup");
  const [newStepsJson, setNewStepsJson] = React.useState(
    '[{"type": "email", "template": "welcome", "delay_hours": 0}]'
  );
  const [creating, setCreating] = React.useState(false);

  /* ── Edit dialog state ── */
  const [editTarget, setEditTarget] = React.useState<Flow | null>(null);
  const [editName, setEditName] = React.useState("");
  const [editDescription, setEditDescription] = React.useState("");
  const [editTriggerType, setEditTriggerType] = React.useState("");
  const [editStepsJson, setEditStepsJson] = React.useState("");
  const [saving, setSaving] = React.useState(false);

  /* ── Lifecycle action state ── */
  const [activateTarget, setActivateTarget] = React.useState<Flow | null>(null);
  const [activating, setActivating] = React.useState(false);
  const [pauseTarget, setPauseTarget] = React.useState<Flow | null>(null);
  const [pausing, setPausing] = React.useState(false);

  /* ── Delete dialog state ── */
  const [deleteTarget, setDeleteTarget] = React.useState<Flow | null>(null);
  const [deleting, setDeleting] = React.useState(false);

  /**
   * Fetch flows from the API with current pagination and status filter.
   */
  async function fetchFlows() {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (statusFilter) params.set("status", statusFilter);

    const { data, error: apiError } = await api.get<PaginatedResponse<Flow>>(
      `/api/v1/flows?${params.toString()}`
    );
    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setFlows(data.items);
      setTotalFlows(data.total);
    }
    setLoading(false);
  }

  /** Fetch on mount and when page/filter changes. */
  React.useEffect(() => {
    fetchFlows();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, statusFilter]);

  /**
   * Create a new flow via the API.
   */
  async function handleCreate() {
    if (!newName.trim()) {
      setError("Flow name is required.");
      return;
    }

    let steps: Record<string, unknown>[] = [];
    try {
      steps = JSON.parse(newStepsJson);
    } catch {
      setError("Steps must be valid JSON array.");
      return;
    }

    setCreating(true);
    setError(null);

    const { error: apiError } = await api.post("/api/v1/flows", {
      name: newName.trim(),
      description: newDescription.trim() || null,
      trigger_type: newTriggerType,
      steps,
    });
    setCreating(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    setCreateOpen(false);
    setNewName("");
    setNewDescription("");
    setNewTriggerType("signup");
    setNewStepsJson(
      '[{"type": "email", "template": "welcome", "delay_hours": 0}]'
    );
    fetchFlows();
  }

  /**
   * Open the edit dialog pre-filled with the selected flow's data.
   *
   * @param flow - The flow to edit.
   */
  function openEditDialog(flow: Flow) {
    setEditTarget(flow);
    setEditName(flow.name);
    setEditDescription(flow.description || "");
    setEditTriggerType(flow.trigger_type);
    setEditStepsJson(
      JSON.stringify(Array.isArray(flow.steps) ? flow.steps : [], null, 2)
    );
  }

  /**
   * Save edits to the selected flow via PATCH.
   */
  async function handleSaveEdit() {
    if (!editTarget) return;

    let steps: Record<string, unknown>[] | undefined;
    if (editStepsJson.trim()) {
      try {
        steps = JSON.parse(editStepsJson);
      } catch {
        setError("Steps must be valid JSON array.");
        return;
      }
    }

    setSaving(true);
    setError(null);

    const { error: apiError } = await api.patch(
      `/api/v1/flows/${editTarget.id}`,
      {
        name: editName.trim() || undefined,
        description: editDescription.trim() || null,
        trigger_type: editTriggerType || undefined,
        steps,
      }
    );
    setSaving(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    setEditTarget(null);
    fetchFlows();
  }

  /**
   * Activate a flow (requires at least one step).
   *
   * @param id - The flow UUID.
   */
  async function handleActivate(id: string) {
    setActivating(true);
    setError(null);

    const { error: apiError } = await api.post(
      `/api/v1/flows/${id}/activate`
    );
    setActivating(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    setActivateTarget(null);
    fetchFlows();
  }

  /**
   * Pause an active flow.
   *
   * @param id - The flow UUID.
   */
  async function handlePause(id: string) {
    setPausing(true);
    setError(null);

    const { error: apiError } = await api.post(`/api/v1/flows/${id}/pause`);
    setPausing(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    setPauseTarget(null);
    fetchFlows();
  }

  /**
   * Delete a flow after user confirmation.
   *
   * @param id - The flow UUID.
   */
  async function handleDelete(id: string) {
    setDeleting(true);
    const { error: apiError } = await api.del(`/api/v1/flows/${id}`);
    setDeleting(false);

    if (apiError) {
      setError(apiError.message);
      return;
    }

    setDeleteTarget(null);
    fetchFlows();
  }

  /** Pagination calculations. */
  const totalPages = Math.max(1, Math.ceil(totalFlows / pageSize));

  /** Count flows by status for KPI cards. */
  const activeCount = flows.filter((f) => f.status === "active").length;
  const draftCount = flows.filter((f) => f.status === "draft").length;
  const pausedCount = flows.filter((f) => f.status === "paused").length;

  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* ── Page Header ── */}
        <FadeIn direction="down">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight">
                Automation Flows
              </h2>
              <p className="text-muted-foreground mt-1">
                Build automated email sequences triggered by subscriber
                actions.
              </p>
            </div>
            <Button onClick={() => setCreateOpen(true)}>
              <Plus className="size-4" />
              New Flow
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
                Total Flows
              </CardTitle>
              <GitBranch className="size-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <AnimatedCounter
                value={totalFlows}
                className="text-3xl font-bold font-heading"
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Active
              </CardTitle>
              <Zap className="size-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              <AnimatedCounter
                value={activeCount}
                className="text-3xl font-bold font-heading text-emerald-600 dark:text-emerald-400"
              />
              <p className="text-xs text-muted-foreground mt-1">
                processing triggers
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Drafts
              </CardTitle>
              <CircleDot className="size-4 text-amber-500" />
            </CardHeader>
            <CardContent>
              <AnimatedCounter
                value={draftCount}
                className="text-3xl font-bold font-heading text-amber-600 dark:text-amber-400"
              />
              <p className="text-xs text-muted-foreground mt-1">
                ready to activate
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Paused
              </CardTitle>
              <Pause className="size-4 text-red-500" />
            </CardHeader>
            <CardContent>
              <AnimatedCounter
                value={pausedCount}
                className="text-3xl font-bold font-heading text-red-600 dark:text-red-400"
              />
              <p className="text-xs text-muted-foreground mt-1">
                temporarily stopped
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

        {/* ── Flow List ── */}
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
                  <Skeleton className="h-8 w-24" />
                </div>
              ))}
            </CardContent>
          </Card>
        ) : flows.length === 0 ? (
          <FadeIn>
            <Card>
              <CardContent className="pt-12 pb-12 text-center">
                <div className="mx-auto size-12 rounded-full bg-muted flex items-center justify-center mb-4">
                  <GitBranch className="size-6 text-muted-foreground" />
                </div>
                <h3 className="font-heading font-semibold text-lg">
                  {statusFilter
                    ? `No ${statusFilter} flows`
                    : "No automation flows yet"}
                </h3>
                <p className="text-muted-foreground text-sm mt-1 max-w-sm mx-auto">
                  {statusFilter
                    ? "Try selecting a different status filter."
                    : "Create your first automation flow to start engaging subscribers automatically."}
                </p>
                {!statusFilter && (
                  <Button className="mt-4" onClick={() => setCreateOpen(true)}>
                    <Plus className="size-4" />
                    Create your first flow
                  </Button>
                )}
              </CardContent>
            </Card>
          </FadeIn>
        ) : (
          <StaggerChildren className="space-y-3" staggerDelay={0.05}>
            {flows.map((flow) => {
              const stepCount = countSteps(flow.steps);
              return (
                <Card key={flow.id} className="py-4">
                  <CardContent className="flex items-center gap-4">
                    {/* Flow status icon */}
                    <div
                      className={cn(
                        "size-10 rounded-lg flex items-center justify-center shrink-0",
                        flow.status === "active"
                          ? "bg-emerald-100 dark:bg-emerald-900/30"
                          : flow.status === "paused"
                            ? "bg-red-100 dark:bg-red-900/30"
                            : "bg-amber-100 dark:bg-amber-900/30"
                      )}
                    >
                      <StatusIcon status={flow.status} />
                    </div>

                    {/* Flow details */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="font-medium truncate">{flow.name}</p>
                        <Badge variant={statusVariant(flow.status)}>
                          {flow.status}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
                        <span className="flex items-center gap-1">
                          <Zap className="size-3" />
                          {getTriggerLabel(flow.trigger_type)}
                        </span>
                        <span>
                          {stepCount} {stepCount === 1 ? "step" : "steps"}
                        </span>
                        {flow.description && (
                          <span className="truncate max-w-[200px]">
                            {flow.description}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Action buttons — vary by status */}
                    <div className="flex items-center gap-1 shrink-0">
                      {flow.status === "active" ? (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setPauseTarget(flow)}
                        >
                          <Pause className="size-3.5" />
                          <span className="hidden sm:inline">Pause</span>
                        </Button>
                      ) : (
                        <>
                          {(flow.status === "draft" ||
                            flow.status === "paused") && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="size-8"
                              onClick={() => openEditDialog(flow)}
                              title="Edit flow"
                            >
                              <Pencil className="size-3.5" />
                            </Button>
                          )}
                          <Button
                            size="sm"
                            onClick={() => setActivateTarget(flow)}
                            title="Activate flow"
                          >
                            <Play className="size-3.5" />
                            <span className="hidden sm:inline">Activate</span>
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="size-8 text-muted-foreground hover:text-destructive"
                            onClick={() => setDeleteTarget(flow)}
                            title="Delete flow"
                          >
                            <Trash2 className="size-3.5" />
                          </Button>
                        </>
                      )}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </StaggerChildren>
        )}

        {/* ── Pagination ── */}
        {!loading && flows.length > 0 && (
          <FadeIn>
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Showing {(page - 1) * pageSize + 1} -{" "}
                {Math.min(page * pageSize, totalFlows)} of{" "}
                {totalFlows.toLocaleString()} flows
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
              <div className="flex items-center gap-2">
                <AlertCircle className="size-4 text-destructive shrink-0" />
                <p className="text-sm text-destructive">{error}</p>
              </div>
            </div>
          </FadeIn>
        )}

        {/* ── Create Flow Dialog ── */}
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>New Automation Flow</DialogTitle>
              <DialogDescription>
                Create an automated email sequence. Define the trigger event,
                add your email steps, then activate when ready.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <label htmlFor="flow-name" className="text-sm font-medium">
                  Flow Name *
                </label>
                <Input
                  id="flow-name"
                  placeholder="e.g. Welcome Series"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="flow-desc" className="text-sm font-medium">
                  Description
                </label>
                <Input
                  id="flow-desc"
                  placeholder="e.g. Onboarding sequence for new subscribers"
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="flow-trigger" className="text-sm font-medium">
                  Trigger Type *
                </label>
                <select
                  id="flow-trigger"
                  value={newTriggerType}
                  onChange={(e) => setNewTriggerType(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1"
                >
                  {TRIGGER_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <label htmlFor="flow-steps" className="text-sm font-medium">
                  Steps (JSON)
                </label>
                <textarea
                  id="flow-steps"
                  rows={5}
                  value={newStepsJson}
                  onChange={(e) => setNewStepsJson(e.target.value)}
                  className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono shadow-xs placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1"
                />
                <p className="text-xs text-muted-foreground">
                  JSON array of step objects. Each step needs &quot;type&quot;,
                  &quot;template&quot;, and &quot;delay_hours&quot;.
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
                {creating ? "Creating..." : "Create Flow"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* ── Edit Flow Dialog ── */}
        <Dialog
          open={editTarget !== null}
          onOpenChange={(open) => {
            if (!open) setEditTarget(null);
          }}
        >
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Edit Flow</DialogTitle>
              <DialogDescription>
                Update the flow configuration. Active flows must be paused
                before editing.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <label htmlFor="edit-flow-name" className="text-sm font-medium">
                  Flow Name
                </label>
                <Input
                  id="edit-flow-name"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="edit-flow-desc" className="text-sm font-medium">
                  Description
                </label>
                <Input
                  id="edit-flow-desc"
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <label
                  htmlFor="edit-flow-trigger"
                  className="text-sm font-medium"
                >
                  Trigger Type
                </label>
                <select
                  id="edit-flow-trigger"
                  value={editTriggerType}
                  onChange={(e) => setEditTriggerType(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1"
                >
                  {TRIGGER_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <label
                  htmlFor="edit-flow-steps"
                  className="text-sm font-medium"
                >
                  Steps (JSON)
                </label>
                <textarea
                  id="edit-flow-steps"
                  rows={5}
                  value={editStepsJson}
                  onChange={(e) => setEditStepsJson(e.target.value)}
                  className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono shadow-xs placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1"
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

        {/* ── Activate Confirmation Dialog ── */}
        <Dialog
          open={activateTarget !== null}
          onOpenChange={(open) => {
            if (!open) setActivateTarget(null);
          }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Activate Flow</DialogTitle>
              <DialogDescription>
                Are you sure you want to activate{" "}
                <strong>&quot;{activateTarget?.name}&quot;</strong>? The flow
                will start processing triggers immediately. It must have at
                least one step defined.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setActivateTarget(null)}
                disabled={activating}
              >
                Cancel
              </Button>
              <Button
                onClick={() =>
                  activateTarget && handleActivate(activateTarget.id)
                }
                disabled={activating}
              >
                {activating && <Loader2 className="size-4 animate-spin" />}
                {activating ? "Activating..." : "Activate Flow"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* ── Pause Confirmation Dialog ── */}
        <Dialog
          open={pauseTarget !== null}
          onOpenChange={(open) => {
            if (!open) setPauseTarget(null);
          }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Pause Flow</DialogTitle>
              <DialogDescription>
                Are you sure you want to pause{" "}
                <strong>&quot;{pauseTarget?.name}&quot;</strong>? The flow
                will stop processing new triggers until reactivated. Existing
                in-progress executions may continue.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setPauseTarget(null)}
                disabled={pausing}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={() => pauseTarget && handlePause(pauseTarget.id)}
                disabled={pausing}
              >
                {pausing && <Loader2 className="size-4 animate-spin" />}
                {pausing ? "Pausing..." : "Pause Flow"}
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
              <DialogTitle>Delete Flow</DialogTitle>
              <DialogDescription>
                Are you sure you want to delete{" "}
                <strong>&quot;{deleteTarget?.name}&quot;</strong>? This will
                permanently remove the flow and all its execution history.
                This action cannot be undone.
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
                {deleting ? "Deleting..." : "Delete Flow"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageTransition>
    </Shell>
  );
}
