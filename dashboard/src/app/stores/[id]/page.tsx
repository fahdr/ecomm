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
import { PageTransition, FadeIn } from "@/components/motion-wrappers";
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
import {
  DollarSign,
  ShoppingCart,
  Package,
  TrendingUp,
  ExternalLink,
  Palette,
  Plus,
} from "lucide-react";
import { InventoryAlerts } from "@/components/inventory-alerts";

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

/** Analytics summary returned by the dashboard endpoint. */
interface AnalyticsSummary {
  total_revenue: string;
  total_orders: number;
  total_products: number;
  average_order_value: string;
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

  // Analytics KPI state.
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [recentOrders, setRecentOrders] = useState<Array<{
    id: string; order_number: string; status: string; total: string; customer_email: string; created_at: string;
  }>>([]);

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

    async function fetchAnalytics() {
      const [summaryRes, ordersRes] = await Promise.all([
        api.get<AnalyticsSummary>(`/api/v1/stores/${storeId}/analytics/summary`),
        api.get<{ items: Array<{ id: string; order_number: string; status: string; total: string; customer_email: string; created_at: string }> }>(
          `/api/v1/stores/${storeId}/orders?per_page=5`
        ),
      ]);
      if (summaryRes.data) setAnalytics(summaryRes.data);
      if (ordersRes.data) {
        const items = Array.isArray(ordersRes.data) ? ordersRes.data : ordersRes.data.items ?? [];
        setRecentOrders(items);
      }
    }

    fetchStore();
    fetchAnalytics();
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
        <FadeIn>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-heading font-bold">{store?.name || "Store Overview"}</h1>
              {store && (
                <Badge variant={store.status === "active" ? "default" : "secondary"}>
                  {store.status}
                </Badge>
              )}
            </div>
            {store && (
              <div className="flex gap-2">
                <Link href={`/stores/${storeId}/products/new`}>
                  <Button variant="outline" size="sm" className="gap-1">
                    <Plus className="h-3.5 w-3.5" />
                    Add Product
                  </Button>
                </Link>
                <Link href={`/stores/${storeId}/themes`}>
                  <Button variant="outline" size="sm" className="gap-1">
                    <Palette className="h-3.5 w-3.5" />
                    Themes
                  </Button>
                </Link>
              </div>
            )}
          </div>
        </FadeIn>

        {/* KPI Cards */}
        {analytics && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: "Revenue", value: `$${Number(analytics.total_revenue).toLocaleString(undefined, { minimumFractionDigits: 2 })}`, icon: DollarSign, color: "text-green-600" },
              { label: "Orders", value: String(analytics.total_orders), icon: ShoppingCart, color: "text-blue-600" },
              { label: "Products", value: String(analytics.total_products), icon: Package, color: "text-purple-600" },
              { label: "Avg Order", value: `$${Number(analytics.average_order_value).toFixed(2)}`, icon: TrendingUp, color: "text-amber-600" },
            ].map((kpi) => (
              <Card key={kpi.label}>
                <CardContent className="pt-5 pb-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{kpi.label}</p>
                      <p className="text-2xl font-bold mt-1">{kpi.value}</p>
                    </div>
                    <div className={`p-2 rounded-lg bg-muted/50 ${kpi.color}`}>
                      <kpi.icon className="h-5 w-5" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Recent Orders */}
        {recentOrders.length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-heading">Recent Orders</CardTitle>
                <Link href={`/stores/${storeId}/orders`}>
                  <Button variant="ghost" size="sm" className="gap-1 text-xs">
                    View All
                    <ExternalLink className="h-3 w-3" />
                  </Button>
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {recentOrders.map((order) => (
                  <Link
                    key={order.id}
                    href={`/stores/${storeId}/orders/${order.id}`}
                    className="flex items-center justify-between p-3 rounded-lg border border-border hover:bg-muted/30 transition-colors"
                  >
                    <div>
                      <span className="text-sm font-medium">{order.order_number}</span>
                      <p className="text-xs text-muted-foreground">{order.customer_email}</p>
                    </div>
                    <div className="text-right">
                      <span className="text-sm font-semibold">${Number(order.total).toFixed(2)}</span>
                      <p className="text-xs capitalize text-muted-foreground">{order.status}</p>
                    </div>
                  </Link>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Inventory Alerts */}
        {storeId && <InventoryAlerts storeId={storeId} />}

        {/* Store Settings */}
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
