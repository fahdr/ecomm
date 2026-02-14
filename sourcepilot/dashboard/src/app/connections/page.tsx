/**
 * Store Connections page — manage connected e-commerce stores.
 *
 * Users connect their Shopify, WooCommerce, or other stores so that
 * imported products are automatically pushed to the correct storefront.
 * One store can be set as the default for quick imports.
 *
 * **For Developers:**
 *   - CRUD operations via `GET/POST/PUT/DELETE /api/v1/connections`.
 *   - Each connection has: id, store_id, name, url, platform, is_default, status.
 *   - Setting a store as default calls `PUT /api/v1/connections/{id}` with `is_default: true`.
 *   - The API should unset other defaults when one is set.
 *
 * **For Project Managers:**
 *   - Store connections determine where imported products are published.
 *   - The default store is pre-selected in import dialogs for faster workflow.
 *   - Multiple stores supported for multi-store merchants.
 *
 * **For QA Engineers:**
 *   - Test creating a connection with valid and invalid URLs.
 *   - Verify setting default unsets previous default.
 *   - Test edit pre-fills all fields correctly.
 *   - Test delete confirmation and cancellation.
 *   - Verify empty state displays when no connections exist.
 *   - Test with long store names — should truncate gracefully.
 *
 * **For End Users:**
 *   - Click "Connect Store" to add a new store.
 *   - Set one store as your default — it will be pre-selected during imports.
 *   - The star icon marks your default store.
 *   - Edit or remove store connections using the action buttons.
 */

"use client";

import * as React from "react";
import {
  Link as LinkIcon,
  Plus,
  Pencil,
  Trash2,
  Loader2,
  Star,
  ExternalLink,
  Globe,
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

/** Shape of a store connection from the API. */
interface StoreConnection {
  id: string;
  store_id: string;
  name: string;
  url: string;
  platform?: string;
  is_default: boolean;
  status: "active" | "inactive";
  products_count?: number;
  created_at: string;
}

/** Form data for creating/editing a store connection. */
interface ConnectionForm {
  store_id: string;
  name: string;
  url: string;
  platform: string;
}

/** Available e-commerce platforms. */
const PLATFORMS = [
  { value: "shopify", label: "Shopify" },
  { value: "woocommerce", label: "WooCommerce" },
  { value: "bigcommerce", label: "BigCommerce" },
  { value: "other", label: "Other" },
];

/**
 * Store Connections page component.
 *
 * @returns The connections page wrapped in the Shell layout.
 */
export default function ConnectionsPage() {
  const [connections, setConnections] = React.useState<StoreConnection[]>([]);
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

  /** Form state. */
  const [form, setForm] = React.useState<ConnectionForm>({
    store_id: "",
    name: "",
    url: "",
    platform: "shopify",
  });

  /**
   * Fetch all store connections from the API.
   */
  const fetchConnections = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    const { data, error: apiError } = await api.get<StoreConnection[]>(
      "/api/v1/connections"
    );
    if (apiError) {
      setError(apiError.message);
    } else if (data) {
      setConnections(data);
    }
    setLoading(false);
  }, []);

  React.useEffect(() => {
    fetchConnections();
  }, [fetchConnections]);

  /**
   * Open the create dialog with an empty form.
   */
  function handleCreate() {
    setEditingId(null);
    setForm({ store_id: "", name: "", url: "", platform: "shopify" });
    setDialogOpen(true);
  }

  /**
   * Open the edit dialog pre-filled with connection data.
   *
   * @param conn - The store connection to edit.
   */
  function handleEdit(conn: StoreConnection) {
    setEditingId(conn.id);
    setForm({
      store_id: conn.store_id,
      name: conn.name,
      url: conn.url,
      platform: conn.platform || "shopify",
    });
    setDialogOpen(true);
  }

  /**
   * Submit the create or edit form to the API.
   */
  async function handleSubmit() {
    if (!form.name.trim() || !form.url.trim()) return;

    setSubmitting(true);
    const payload = {
      store_id: form.store_id.trim(),
      name: form.name.trim(),
      url: form.url.trim(),
      platform: form.platform,
    };

    if (editingId) {
      await api.patch(`/api/v1/connections/${editingId}`, payload);
    } else {
      await api.post("/api/v1/connections", payload);
    }

    setSubmitting(false);
    setDialogOpen(false);
    fetchConnections();
  }

  /**
   * Set a connection as the default store.
   *
   * @param id - The connection ID to set as default.
   */
  async function handleSetDefault(id: string) {
    await api.patch(`/api/v1/connections/${id}`, { is_default: true });
    fetchConnections();
  }

  /**
   * Open the delete confirmation dialog.
   *
   * @param id - The connection ID to delete.
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
    await api.del(`/api/v1/connections/${deletingId}`);
    setDeleting(false);
    setDeleteDialogOpen(false);
    setDeletingId(null);
    fetchConnections();
  }

  return (
    <Shell>
      <PageTransition className="p-6 space-y-8">
        {/* ── Header ── */}
        <FadeIn direction="down">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-heading text-2xl font-bold tracking-tight">
                Store Connections
              </h2>
              <p className="text-muted-foreground mt-1">
                Connect your e-commerce stores to receive imported products
              </p>
            </div>
            <Button onClick={handleCreate}>
              <Plus className="size-4" />
              Connect Store
            </Button>
          </div>
        </FadeIn>

        {/* ── Error State ── */}
        {error && (
          <FadeIn>
            <Card className="border-destructive/50">
              <CardContent className="pt-6">
                <p className="text-destructive text-sm">
                  Failed to load store connections: {error}
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={fetchConnections}
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
                      <Skeleton className="h-3 w-48" />
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-8 w-24 mt-3" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : connections.length === 0 && !error ? (
          /* ── Empty State ── */
          <FadeIn>
            <Card>
              <CardContent className="pt-6 text-center py-12">
                <LinkIcon className="size-12 text-muted-foreground/40 mx-auto mb-4" />
                <h3 className="font-heading text-lg font-semibold mb-2">
                  No stores connected
                </h3>
                <p className="text-muted-foreground text-sm mb-4">
                  Connect your first e-commerce store to start importing products.
                </p>
                <Button onClick={handleCreate}>
                  <Plus className="size-4" />
                  Connect Your First Store
                </Button>
              </CardContent>
            </Card>
          </FadeIn>
        ) : (
          /* ── Connections Grid ── */
          <StaggerChildren
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
            staggerDelay={0.08}
          >
            {connections.map((conn) => (
              <Card
                key={conn.id}
                className={`hover:border-primary/30 transition-colors ${
                  conn.is_default ? "border-primary/40 bg-primary/[0.02]" : ""
                }`}
              >
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 min-w-0">
                      {/* Store icon */}
                      <div className="size-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                        <Globe className="size-5 text-primary" />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <CardTitle className="text-base truncate">
                            {conn.name}
                          </CardTitle>
                          {conn.is_default && (
                            <Star className="size-4 text-amber-500 fill-amber-500 shrink-0" />
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground truncate mt-0.5">
                          {conn.url}
                        </p>
                      </div>
                    </div>
                    <Badge
                      variant={
                        conn.status === "active" ? "success" : "secondary"
                      }
                    >
                      {conn.status}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground mb-4">
                    <span className="capitalize">
                      {PLATFORMS.find((p) => p.value === conn.platform)?.label ||
                        conn.platform ||
                        "Unknown"}
                    </span>
                    {conn.products_count !== undefined && (
                      <>
                        <span>&middot;</span>
                        <span>{conn.products_count} products</span>
                      </>
                    )}
                    <span>&middot;</span>
                    <span>ID: {conn.store_id}</span>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    {!conn.is_default && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleSetDefault(conn.id)}
                        title="Set as default store"
                      >
                        <Star className="size-3" />
                        Set Default
                      </Button>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEdit(conn)}
                    >
                      <Pencil className="size-3" />
                      Edit
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-destructive hover:text-destructive"
                      onClick={() => confirmDelete(conn.id)}
                    >
                      <Trash2 className="size-3" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      asChild
                      title="Open store"
                    >
                      <a
                        href={conn.url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <ExternalLink className="size-4" />
                      </a>
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
                {editingId ? "Edit Store Connection" : "Connect Store"}
              </DialogTitle>
              <DialogDescription>
                {editingId
                  ? "Update your store connection details."
                  : "Enter your store details to connect it for product imports."}
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2">
              {/* Platform */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Platform</label>
                <select
                  value={form.platform}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, platform: e.target.value }))
                  }
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {PLATFORMS.map((p) => (
                    <option key={p.value} value={p.value}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Store Name */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Store Name</label>
                <Input
                  placeholder="My Shopify Store"
                  value={form.name}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, name: e.target.value }))
                  }
                />
              </div>

              {/* Store URL */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Store URL</label>
                <Input
                  type="url"
                  placeholder="https://mystore.myshopify.com"
                  value={form.url}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, url: e.target.value }))
                  }
                />
              </div>

              {/* Store ID */}
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  Store ID{" "}
                  <span className="text-muted-foreground font-normal">
                    (optional)
                  </span>
                </label>
                <Input
                  placeholder="store_abc123"
                  value={form.store_id}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, store_id: e.target.value }))
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
                disabled={submitting || !form.name.trim() || !form.url.trim()}
              >
                {submitting ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : editingId ? (
                  <Pencil className="size-4" />
                ) : (
                  <LinkIcon className="size-4" />
                )}
                {submitting
                  ? "Saving..."
                  : editingId
                    ? "Save Changes"
                    : "Connect Store"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* ── Delete Confirmation Dialog ── */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent className="sm:max-w-sm">
            <DialogHeader>
              <DialogTitle className="font-heading">
                Remove Store Connection
              </DialogTitle>
              <DialogDescription>
                This will disconnect this store. Products already imported will
                not be affected, but new imports will no longer be sent to this
                store. This action cannot be undone.
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
                {deleting ? "Removing..." : "Remove Store"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageTransition>
    </Shell>
  );
}
