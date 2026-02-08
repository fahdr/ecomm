/**
 * Bulk Operations page.
 *
 * Provides forms for executing bulk operations on store products, including
 * bulk price updates (percentage or fixed amount) and bulk product deletion.
 *
 * **For End Users:**
 *   Make mass changes to your product catalog without editing items one
 *   by one. Increase or decrease all prices by a percentage or fixed
 *   amount. Remove products in bulk by entering their IDs.
 *
 * **For Developers:**
 *   - Bulk price update via `POST /api/v1/stores/{store_id}/bulk/price`.
 *   - Bulk delete via `POST /api/v1/stores/{store_id}/bulk/delete`.
 *   - Price update payload: `{ mode, value, product_ids? }`.
 *   - Delete payload: `{ product_ids }`.
 *
 * **For QA Engineers:**
 *   - Verify that the percentage adjustment accepts negative values (discount).
 *   - Verify that the fixed-amount adjustment applies correctly.
 *   - Verify that the delete operation requires a confirmation dialog.
 *   - Verify that product IDs are parsed correctly from comma-separated input.
 *   - Verify success and error messages display appropriately.
 *
 * **For Project Managers:**
 *   This page corresponds to Feature 26 (Bulk Ops) in the backlog.
 *   Bulk operations save time when managing large product catalogs.
 */

"use client";

import { FormEvent, useState, use } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";

/** Response shape from bulk operations. */
interface BulkResult {
  affected_count: number;
  message: string;
}

/**
 * BulkOperationsPage renders forms for bulk price updates and bulk deletion.
 *
 * @param params - Route parameters containing the store ID.
 * @returns The rendered bulk operations page.
 */
export default function BulkOperationsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { loading: authLoading } = useAuth();

  /* Bulk price update state */
  const [priceMode, setPriceMode] = useState<"percentage" | "fixed">(
    "percentage"
  );
  const [priceValue, setPriceValue] = useState("");
  const [priceProductIds, setPriceProductIds] = useState("");
  const [priceUpdating, setPriceUpdating] = useState(false);
  const [priceError, setPriceError] = useState<string | null>(null);
  const [priceSuccess, setPriceSuccess] = useState<string | null>(null);

  /* Bulk delete state */
  const [deleteProductIds, setDeleteProductIds] = useState("");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteSuccess, setDeleteSuccess] = useState<string | null>(null);

  /**
   * Handle the bulk price update form submission.
   *
   * @param e - The form submission event.
   */
  async function handlePriceUpdate(e: FormEvent) {
    e.preventDefault();
    setPriceUpdating(true);
    setPriceError(null);
    setPriceSuccess(null);

    const productIds = priceProductIds
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    const result = await api.post<BulkResult>(
      `/api/v1/stores/${id}/bulk/products/price`,
      {
        adjustment_type: priceMode,
        adjustment_value: parseFloat(priceValue),
        product_ids: productIds.length > 0 ? productIds : undefined,
      }
    );

    if (result.error) {
      setPriceError(result.error.message);
    } else if (result.data) {
      setPriceSuccess(
        `Updated ${result.data.affected_count} product${result.data.affected_count !== 1 ? "s" : ""} successfully.`
      );
      setPriceValue("");
      setPriceProductIds("");
    }
    setPriceUpdating(false);
    if (result.data) {
      setTimeout(() => setPriceSuccess(null), 5000);
    }
  }

  /**
   * Handle the bulk delete confirmation.
   * Parses product IDs from the text area and sends the delete request.
   */
  async function handleBulkDelete() {
    setDeleting(true);
    setDeleteError(null);
    setDeleteSuccess(null);

    const productIds = deleteProductIds
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    if (productIds.length === 0) {
      setDeleteError("Enter at least one product ID.");
      setDeleting(false);
      return;
    }

    const result = await api.post<BulkResult>(
      `/api/v1/stores/${id}/bulk/products/delete`,
      { product_ids: productIds }
    );

    if (result.error) {
      setDeleteError(result.error.message);
    } else if (result.data) {
      setDeleteSuccess(
        `Deleted ${result.data.affected_count} product${result.data.affected_count !== 1 ? "s" : ""} successfully.`
      );
      setDeleteProductIds("");
    }
    setDeleting(false);
    setDeleteDialogOpen(false);
    if (result.data) {
      setTimeout(() => setDeleteSuccess(null), 5000);
    }
  }

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
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
          <Link
            href={`/stores/${id}`}
            className="text-lg font-semibold hover:underline"
          >
            Store
          </Link>
          <span className="text-muted-foreground">/</span>
          <h1 className="text-lg font-semibold">Bulk Operations</h1>
        </div>
      </header>

      <main className="mx-auto max-w-2xl space-y-6 p-6">
        {/* Bulk Price Update */}
        <Card>
          <CardHeader>
            <CardTitle>Bulk Price Update</CardTitle>
            <CardDescription>
              Adjust prices across your entire catalog or a subset of products.
              Use a percentage for proportional changes or a fixed amount for
              absolute adjustments.
            </CardDescription>
          </CardHeader>
          <form onSubmit={handlePriceUpdate}>
            <CardContent className="space-y-4">
              {priceError && (
                <p className="text-sm text-destructive">{priceError}</p>
              )}
              {priceSuccess && (
                <p className="text-sm text-green-600">{priceSuccess}</p>
              )}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="price-mode">Adjustment Mode</Label>
                  <Select
                    value={priceMode}
                    onValueChange={(v) =>
                      setPriceMode(v as "percentage" | "fixed")
                    }
                  >
                    <SelectTrigger id="price-mode">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="percentage">Percentage (%)</SelectItem>
                      <SelectItem value="fixed">Fixed Amount ($)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="price-value">
                    {priceMode === "percentage" ? "Percentage" : "Amount"}
                  </Label>
                  <Input
                    id="price-value"
                    type="number"
                    step="0.01"
                    placeholder={priceMode === "percentage" ? "10" : "5.00"}
                    value={priceValue}
                    onChange={(e) => setPriceValue(e.target.value)}
                    required
                  />
                  <p className="text-xs text-muted-foreground">
                    Use negative values to decrease prices.
                  </p>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="price-ids">
                  Product IDs{" "}
                  <span className="text-muted-foreground font-normal">
                    (optional, comma-separated)
                  </span>
                </Label>
                <Textarea
                  id="price-ids"
                  placeholder="Leave empty to apply to all products, or enter specific IDs..."
                  value={priceProductIds}
                  onChange={(e) => setPriceProductIds(e.target.value)}
                  rows={2}
                />
              </div>
            </CardContent>
            <CardFooter className="flex justify-end">
              <Button type="submit" disabled={priceUpdating}>
                {priceUpdating ? "Updating..." : "Update Prices"}
              </Button>
            </CardFooter>
          </form>
        </Card>

        <Separator />

        {/* Bulk Delete */}
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="text-destructive">
              Bulk Delete Products
            </CardTitle>
            <CardDescription>
              Permanently remove multiple products at once. This action cannot
              be undone.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {deleteError && (
              <p className="text-sm text-destructive">{deleteError}</p>
            )}
            {deleteSuccess && (
              <p className="text-sm text-green-600">{deleteSuccess}</p>
            )}
            <div className="space-y-2">
              <Label htmlFor="delete-ids">Product IDs (comma-separated)</Label>
              <Textarea
                id="delete-ids"
                placeholder="product-id-1, product-id-2, ..."
                value={deleteProductIds}
                onChange={(e) => setDeleteProductIds(e.target.value)}
                rows={3}
              />
            </div>
            <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
              <DialogTrigger asChild>
                <Button
                  variant="destructive"
                  disabled={!deleteProductIds.trim()}
                >
                  Delete Products
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Confirm Bulk Deletion</DialogTitle>
                  <DialogDescription>
                    You are about to delete{" "}
                    {
                      deleteProductIds
                        .split(",")
                        .map((s) => s.trim())
                        .filter(Boolean).length
                    }{" "}
                    product(s). This action is permanent and cannot be undone.
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
                    onClick={handleBulkDelete}
                    disabled={deleting}
                  >
                    {deleting ? "Deleting..." : "Confirm Delete"}
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
