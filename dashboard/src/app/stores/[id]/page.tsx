/**
 * Store settings page.
 *
 * Displays the details of a single store and provides forms to update
 * its settings or delete it. Uses the store context for the store ID
 * and fetches the full store record for local editing state.
 *
 * **For End Users:**
 *   View and edit your store's name, niche, and description. You can
 *   also pause or delete the store from this page.
 *
 * **For QA Engineers:**
 *   - The page reads the store ID from the shared StoreProvider context.
 *   - Store details are fetched for the edit form (name, niche, description, status).
 *   - If the store is not found (404) or belongs to another user, a
 *     "Store not found" message is shown.
 *   - The delete button shows a confirmation dialog before soft-deleting.
 *   - After deletion, the user is redirected to `/stores`.
 *   - Updating the name triggers slug regeneration on the backend.
 *
 * **For Developers:**
 *   - Uses `useStore()` from the store context to obtain the store ID.
 *   - Wrapped in `<PageTransition>` for consistent page entrance animations.
 *   - The old breadcrumb header and Quick Links card have been removed;
 *     navigation is handled by the shell sidebar.
 *
 * **For Project Managers:**
 *   Part of the core store management flow. The settings page is the
 *   landing page for each store in the dashboard.
 */

"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import { PageTransition } from "@/components/motion-wrappers";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

/** Predefined niche categories for the store. */
const NICHES = [
  "Electronics",
  "Fashion",
  "Home & Garden",
  "Health & Beauty",
  "Sports & Outdoors",
  "Toys & Games",
  "Pet Supplies",
  "Automotive",
  "Office Supplies",
  "Food & Beverages",
  "Other",
];

/** Store data returned by the API. */
interface Store {
  id: string;
  name: string;
  slug: string;
  niche: string;
  description: string | null;
  status: "active" | "paused" | "deleted";
  created_at: string;
  updated_at: string;
}

/**
 * Store settings page component.
 *
 * Renders an editable form for the store's name, niche, description,
 * and status, plus a danger-zone section with a delete confirmation dialog.
 *
 * @returns The store settings page wrapped in a PageTransition.
 */
export default function StoreSettingsPage() {
  const { store: contextStore } = useStore();
  const storeId = contextStore?.id;
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [store, setStore] = useState<Store | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  // Edit form state.
  const [name, setName] = useState("");
  const [niche, setNiche] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState<"active" | "paused">("active");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Delete state.
  const [deleting, setDeleting] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  useEffect(() => {
    if (authLoading || !user || !storeId) return;

    /**
     * Fetch the full store record from the API to populate the edit form.
     */
    async function fetchStore() {
      const result = await api.get<Store>(`/api/v1/stores/${storeId}`);
      if (result.error) {
        setNotFound(true);
        setLoading(false);
        return;
      }
      const s = result.data!;
      setStore(s);
      setName(s.name);
      setNiche(s.niche);
      setDescription(s.description || "");
      setStatus(s.status === "paused" ? "paused" : "active");
      setLoading(false);
    }

    fetchStore();
  }, [storeId, user, authLoading]);

  /**
   * Handle the update form submission.
   *
   * Sends a PATCH request to update the store and shows success/error feedback.
   * @param e - The form submission event.
   */
  async function handleUpdate(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);

    const result = await api.patch<Store>(`/api/v1/stores/${storeId}`, {
      name,
      niche,
      description: description || null,
      status,
    });

    if (result.error) {
      setSaveError(result.error.message);
      setSaving(false);
      return;
    }

    setStore(result.data!);
    setSaveSuccess(true);
    setSaving(false);
    setTimeout(() => setSaveSuccess(false), 3000);
  }

  /**
   * Handle the delete confirmation.
   *
   * Sends a DELETE request to soft-delete the store and redirects to /stores.
   */
  async function handleDelete() {
    setDeleting(true);
    await api.delete(`/api/v1/stores/${storeId}`);
    setDeleteDialogOpen(false);
    router.push("/stores");
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-muted-foreground">Loading store...</p>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-20">
        <h2 className="text-xl font-semibold">Store not found</h2>
        <Link href="/stores">
          <Button variant="outline">Back to stores</Button>
        </Link>
      </div>
    );
  }

  return (
    <PageTransition>
      <main className="mx-auto max-w-4xl p-6 space-y-6">
        {/* Page heading */}
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-heading font-bold">Store Settings</h1>
          {store && (
            <Badge variant={store.status === "active" ? "default" : "secondary"}>
              {store.status}
            </Badge>
          )}
        </div>

        {/* Store Info */}
        <Card>
          <CardHeader>
            <CardTitle>Store Details</CardTitle>
            <CardDescription>
              Slug: <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{store?.slug}</code>
            </CardDescription>
          </CardHeader>
          <form onSubmit={handleUpdate}>
            <CardContent className="space-y-4">
              {saveError && (
                <p className="text-sm text-destructive">{saveError}</p>
              )}
              {saveSuccess && (
                <p className="text-sm text-green-600">Store updated successfully.</p>
              )}
              <div className="space-y-2">
                <Label htmlFor="name">Store Name</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  maxLength={255}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="niche">Niche</Label>
                <Select value={niche} onValueChange={setNiche}>
                  <SelectTrigger id="niche">
                    <SelectValue placeholder="Select a niche" />
                  </SelectTrigger>
                  <SelectContent>
                    {NICHES.map((n) => (
                      <SelectItem key={n} value={n.toLowerCase()}>
                        {n}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="status">Status</Label>
                <Select value={status} onValueChange={(v) => setStatus(v as "active" | "paused")}>
                  <SelectTrigger id="status">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="paused">Paused</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
            <CardFooter className="flex justify-end">
              <Button type="submit" disabled={saving}>
                {saving ? "Saving..." : "Save Changes"}
              </Button>
            </CardFooter>
          </form>
        </Card>

        {/* Danger Zone */}
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="text-destructive">Danger Zone</CardTitle>
            <CardDescription>
              Deleting a store is permanent and cannot be undone.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="destructive">Delete Store</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Delete &quot;{store?.name}&quot;?</DialogTitle>
                  <DialogDescription>
                    This action cannot be undone. The store and all its data will
                    be permanently removed.
                  </DialogDescription>
                </DialogHeader>
                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={() => setDeleteDialogOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={handleDelete}
                    disabled={deleting}
                  >
                    {deleting ? "Deleting..." : "Delete"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </CardContent>
        </Card>
      </main>
    </PageTransition>
  );
}
