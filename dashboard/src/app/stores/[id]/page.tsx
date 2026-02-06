/**
 * Store settings page.
 *
 * Displays the details of a single store and provides forms to update
 * its settings or delete it. Loaded by store ID from the URL.
 *
 * **For End Users:**
 *   View and edit your store's name, niche, and description. You can
 *   also pause or delete the store from this page.
 *
 * **For QA Engineers:**
 *   - The page loads the store by ID from the URL parameter.
 *   - If the store is not found (404) or belongs to another user, a
 *     "Store not found" message is shown.
 *   - The delete button shows a confirmation dialog before soft-deleting.
 *   - After deletion, the user is redirected to `/stores`.
 *   - Updating the name triggers slug regeneration on the backend.
 */

"use client";

import { FormEvent, useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
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

export default function StoreSettingsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
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
    if (authLoading || !user) return;

    async function fetchStore() {
      const result = await api.get<Store>(`/api/v1/stores/${id}`);
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
  }, [id, user, authLoading]);

  /**
   * Handle the update form submission.
   */
  async function handleUpdate(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);

    const result = await api.patch<Store>(`/api/v1/stores/${id}`, {
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
   */
  async function handleDelete() {
    setDeleting(true);
    await api.delete(`/api/v1/stores/${id}`);
    setDeleteDialogOpen(false);
    router.push("/stores");
  }

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading store...</p>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4">
        <h2 className="text-xl font-semibold">Store not found</h2>
        <Link href="/stores">
          <Button variant="outline">Back to stores</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b px-6 py-4">
        <div className="flex items-center gap-4">
          <Link href="/stores" className="text-lg font-semibold hover:underline">
            Stores
          </Link>
          <span className="text-muted-foreground">/</span>
          <h1 className="text-lg font-semibold">{store?.name}</h1>
          {store && (
            <Badge variant={store.status === "active" ? "default" : "secondary"}>
              {store.status}
            </Badge>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-2xl space-y-6 p-6">
        {/* Quick Links */}
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-2">
              <Link href={`/stores/${id}/products`}>
                <Button variant="outline" className="w-full justify-start">
                  Manage Products
                </Button>
              </Link>
              <Link href={`/stores/${id}/orders`}>
                <Button variant="outline" className="w-full justify-start">
                  View Orders
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>

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
    </div>
  );
}
