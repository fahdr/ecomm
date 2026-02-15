/**
 * Supplier Accounts page — manage connections to supplier platforms.
 *
 * Users connect their supplier accounts (AliExpress, CJ, Spocket, or custom)
 * by providing API credentials. Connected accounts enable automated imports,
 * price monitoring, and inventory sync.
 *
 * **For Developers:**
 *   - CRUD operations via `GET/POST/PUT/DELETE /api/v1/suppliers/accounts`.
 *   - Supplier types: aliexpress, cj, spocket, custom.
 *   - Each account has a status (active/inactive) and last_synced timestamp.
 *   - Edit reuses the same dialog as create, prefilled with existing data.
 *   - Confirm dialog before delete to prevent accidental removal.
 *
 * **For Project Managers:**
 *   - Supplier accounts are prerequisites for automated imports.
 *   - Status indicators show connection health at a glance.
 *   - Users can manage multiple accounts per supplier type.
 *
 * **For QA Engineers:**
 *   - Test creating an account with each supplier type.
 *   - Verify edit pre-fills all fields correctly.
 *   - Test delete confirmation dialog (Cancel should not delete).
 *   - Verify status badges (active = green, inactive = muted).
 *   - Test with empty supplier list — should show empty state.
 *   - Verify form validation (name and API key required).
 *
 * **For End Users:**
 *   - Click "Connect Supplier" to add a new supplier account.
 *   - Choose the supplier type, give it a name, and enter your API key.
 *   - Active accounts show a green badge; inactive ones need attention.
 *   - Edit or delete accounts using the buttons on each card.
 */

"use client";

import * as React from "react";
import {
  Building2,
  Plus,
  Pencil,
  Trash2,
  Loader2,
  CheckCircle2,
  XCircle,
  RefreshCw,
} from "lucide-react";
import { Shell } from "@/components/shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
} from "@/components/ui/dialog";
import { FadeIn, StaggerChildren, PageTransition } from "@/components/motion";
import { api } from "@/lib/api";

/** Shape of a supplier account from the API. */
interface SupplierAccount {
  id: string;
  type: string;
  name: string;
  api_key: string;
  status: "active" | "inactive";
  last_synced?: string;
  created_at: string;
}

/** Form data for creating/editing a supplier account. */
interface SupplierForm {
  type: string;
  name: string;
  api_key: string;
}

/** Available supplier types. */
const SUPPLIER_TYPES = [
  { value: "aliexpress", label: "AliExpress" },
  { value: "cj", label: "CJ Dropshipping" },
  { value: "spocket", label: "Spocket" },
  { value: "custom", label: "Custom" },
];

/**
 * Supplier Accounts page component.
 *
 * @returns The supplier accounts page wrapped in the Shell layout.
 */
export default function SuppliersPage() {
  const [accounts, setAccounts] = React.useState<SupplierAccount[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  /** Dialog state for create/edit. */
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  /** Delete confirmation state. */
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false);
  const [deletingId, setDeletingId] = React.useState<string | null>(null);
  const [deleting, setDeleting] = React.useState(false);

  /** Form state for create/edit dialog. */
  const [form, setForm] = React.useState<SupplierForm>({
    type: "aliexpress",
    name: "",
    api_key: "",
  });

  /**
   * Fetch all supplier accounts from the API.
   */
  const fetchAccounts = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    const { data, error: apiError } = await api.get<SupplierAccount[]>(
      "/api/v1/suppliers/accounts"
    );
    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setAccounts(data);
    }
    setLoading(false);
  }, []);

  React.useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  /**
   * Open the create dialog with an empty form.
   */
  function handleCreate() {
    setEditingId(null);
    setForm({ type: "aliexpress", name: "", api_key: "" });
    setDialogOpen(true);
  }

  /**
   * Open the edit dialog with pre-filled data from an existing account.
   *
   * @param account - The supplier account to edit.
   */
  function handleEdit(account: SupplierAccount) {
    setEditingId(account.id);
    setForm({
      type: account.type,
      name: account.name,
      api_key: account.api_key,
    });
    setDialogOpen(true);
  }

  /**
   * Submit the create or edit form.
   * POSTs for new accounts, PUTs for edits.
   */
  async function handleSubmit() {
    if (!form.name.trim() || !form.api_key.trim()) return;

    setSubmitting(true);
    const payload = {
      type: form.type,
      name: form.name.trim(),
      api_key: form.api_key.trim(),
    };

    if (editingId) {
      await api.patch(`/api/v1/suppliers/accounts/${editingId}`, payload);
    } else {
      await api.post("/api/v1/suppliers/accounts", payload);
    }

    setSubmitting(false);
    setDialogOpen(false);
    fetchAccounts();
  }

  /**
   * Open the delete confirmation dialog.
   *
   * @param id - The supplier account ID to delete.
   */
  function confirmDelete(id: string) {
    setDeletingId(id);
    setDeleteDialogOpen(true);
  }

  /**
   * Execute the delete after confirmation.
   */
  async function handleDelete() {
    if (!deletingId) return;

    setDeleting(true);
    await api.del(`/api/v1/suppliers/accounts/${deletingId}`);
    setDeleting(false);
    setDeleteDialogOpen(false);
    setDeletingId(null);
    fetchAccounts();
  }

  /**
   * Format a relative time string from an ISO timestamp.
   *
   * @param dateStr - ISO date string.
   * @returns A human-readable relative time (e.g., "2 hours ago").
   */
  function formatRelativeTime(dateStr: string): string {
    const now = Date.now();
    const then = new Date(dateStr).getTime();
    const diffMs = now - then;
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  }

  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* ── Header ── */}
        <FadeIn direction="down">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight">
                Supplier Accounts
              </h2>
              <p className="text-muted-foreground mt-1">
                Connect and manage your supplier platform accounts
              </p>
            </div>
            <Button onClick={handleCreate}>
              <Plus className="size-4" />
              Connect Supplier
            </Button>
          </div>
        </FadeIn>

        {/* ── Error State ── */}
        {error && (
          <FadeIn>
            <Card className="border-destructive/50">
              <CardContent className="pt-6">
                <p className="text-destructive text-sm">
                  Failed to load supplier accounts: {error}
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={fetchAccounts}
                >
                  Retry
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        )}

        {/* ── Loading State ── */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <Skeleton className="size-10 rounded-lg" />
                    <div className="space-y-2">
                      <Skeleton className="h-4 w-32" />
                      <Skeleton className="h-3 w-20" />
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-2/3 mt-2" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : accounts.length === 0 && !error ? (
          /* ── Empty State ── */
          <FadeIn>
            <Card>
              <CardContent className="pt-6 text-center py-12">
                <Building2 className="size-12 text-muted-foreground/40 mx-auto mb-4" />
                <h3 className="font-heading text-lg font-semibold mb-2">
                  No supplier accounts connected
                </h3>
                <p className="text-muted-foreground text-sm mb-4">
                  Connect your first supplier account to start importing products
                  automatically.
                </p>
                <Button onClick={handleCreate}>
                  <Plus className="size-4" />
                  Connect Your First Supplier
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        ) : (
          /* ── Accounts Grid ── */
          <StaggerChildren
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
            staggerDelay={0.08}
          >
            {accounts.map((account) => (
              <Card
                key={account.id}
                className="hover:border-primary/30 transition-colors"
              >
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {/* Supplier type icon */}
                      <div className="size-10 rounded-lg bg-primary/10 flex items-center justify-center">
                        <Building2 className="size-5 text-primary" />
                      </div>
                      <div>
                        <CardTitle className="text-base">
                          {account.name}
                        </CardTitle>
                        <p className="text-xs text-muted-foreground capitalize mt-0.5">
                          {SUPPLIER_TYPES.find((t) => t.value === account.type)
                            ?.label || account.type}
                        </p>
                      </div>
                    </div>
                    <Badge
                      variant={
                        account.status === "active" ? "success" : "secondary"
                      }
                    >
                      {account.status === "active" ? (
                        <CheckCircle2 className="size-3 mr-1" />
                      ) : (
                        <XCircle className="size-3 mr-1" />
                      )}
                      {account.status}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  {/* API Key (masked) */}
                  <div className="text-xs text-muted-foreground mb-3">
                    <span className="font-medium">API Key:</span>{" "}
                    <span className="font-mono">
                      {account.api_key.slice(0, 8)}{"****"}
                    </span>
                  </div>

                  {/* Last synced */}
                  {account.last_synced && (
                    <div className="flex items-center gap-1 text-xs text-muted-foreground mb-4">
                      <RefreshCw className="size-3" />
                      Last synced: {formatRelativeTime(account.last_synced)}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEdit(account)}
                    >
                      <Pencil className="size-3" />
                      Edit
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-destructive hover:text-destructive"
                      onClick={() => confirmDelete(account.id)}
                    >
                      <Trash2 className="size-3" />
                      Delete
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </StaggerChildren>
        )}

        {/* ── Create/Edit Dialog ── */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="font-heading">
                {editingId ? "Edit Supplier Account" : "Connect Supplier"}
              </DialogTitle>
              <DialogDescription>
                {editingId
                  ? "Update the supplier account details below."
                  : "Enter your supplier platform credentials to connect."}
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2">
              {/* Supplier Type */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Supplier Type</label>
                <select
                  value={form.type}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, type: e.target.value }))
                  }
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {SUPPLIER_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Account Name */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Account Name</label>
                <Input
                  placeholder="My AliExpress Account"
                  value={form.name}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, name: e.target.value }))
                  }
                />
              </div>

              {/* API Key */}
              <div className="space-y-2">
                <label className="text-sm font-medium">API Key</label>
                <Input
                  type="password"
                  placeholder="Enter your API key or token"
                  value={form.api_key}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, api_key: e.target.value }))
                  }
                />
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
              <Button
                onClick={handleSubmit}
                disabled={
                  submitting || !form.name.trim() || !form.api_key.trim()
                }
              >
                {submitting ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : editingId ? (
                  <Pencil className="size-4" />
                ) : (
                  <Plus className="size-4" />
                )}
                {submitting
                  ? "Saving..."
                  : editingId
                    ? "Save Changes"
                    : "Connect"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* ── Delete Confirmation Dialog ── */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent className="sm:max-w-sm">
            <DialogHeader>
              <DialogTitle className="font-heading">
                Delete Supplier Account
              </DialogTitle>
              <DialogDescription>
                This will permanently remove this supplier account. Any active
                imports using this account will stop working. This action cannot
                be undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setDeleteDialogOpen(false)}
                disabled={deleting}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleDelete}
                disabled={deleting}
              >
                {deleting ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Trash2 className="size-4" />
                )}
                {deleting ? "Deleting..." : "Delete Account"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageTransition>
    </Shell>
  );
}
