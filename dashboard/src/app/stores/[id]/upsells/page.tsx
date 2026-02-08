/**
 * Upsells management page.
 *
 * Lists all upsell/cross-sell configurations for a store and provides
 * a dialog to create new upsell relationships between products.
 *
 * **For End Users:**
 *   Configure product upsells and cross-sells to increase average order
 *   value. Link a source product to a target product and choose the
 *   upsell type (upsell, cross-sell, or bundle).
 *
 * **For Developers:**
 *   - Fetches upsells via `GET /api/v1/stores/{store_id}/upsells`.
 *   - Creates new upsells via `POST /api/v1/stores/{store_id}/upsells`.
 *   - Upsell types: "upsell", "cross_sell", "bundle".
 *   - Source and target products are referenced by product ID.
 *
 * **For QA Engineers:**
 *   - Verify the upsell list refreshes after creating a new entry.
 *   - Verify that source and target product IDs are required.
 *   - Verify that the type selector defaults to "upsell".
 *   - Verify empty state is shown when no upsells exist.
 *
 * **For Project Managers:**
 *   This page corresponds to Feature 18 (Upsells) in the backlog.
 *   Upsells increase average order value through product recommendations.
 */

"use client";

import { FormEvent, useEffect, useState, use } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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

/** Shape of an upsell configuration returned by the API. */
interface Upsell {
  id: string;
  source_product_id: string;
  target_product_id: string;
  upsell_type: "upsell" | "cross_sell" | "bundle";
  position: number;
  is_active: boolean;
  created_at: string;
}

/**
 * UpsellsPage renders the upsell/cross-sell listing and creation dialog.
 *
 * @param params - Route parameters containing the store ID.
 * @returns The rendered upsells management page.
 */
export default function UpsellsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { user, loading: authLoading } = useAuth();
  const [upsells, setUpsells] = useState<Upsell[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* Create form state */
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formSourceId, setFormSourceId] = useState("");
  const [formTargetId, setFormTargetId] = useState("");
  const [formType, setFormType] = useState<"upsell" | "cross_sell" | "bundle">(
    "upsell"
  );
  const [formPriority, setFormPriority] = useState("0");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  /**
   * Fetch all upsells for this store.
   */
  async function fetchUpsells() {
    setLoading(true);
    const result = await api.get<{ items: Upsell[]; total: number }>(
      `/api/v1/stores/${id}/upsells`
    );
    if (result.error) {
      setError(result.error.message);
    } else {
      setUpsells(result.data?.items ?? []);
    }
    setLoading(false);
  }

  useEffect(() => {
    if (authLoading || !user) return;
    fetchUpsells();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, user, authLoading]);

  /**
   * Handle the create-upsell form submission.
   *
   * @param e - The form submission event.
   */
  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    setCreateError(null);

    const result = await api.post<Upsell>(
      `/api/v1/stores/${id}/upsells`,
      {
        source_product_id: formSourceId,
        target_product_id: formTargetId,
        upsell_type: formType,
        position: parseInt(formPriority, 10),
      }
    );

    if (result.error) {
      setCreateError(result.error.message);
      setCreating(false);
      return;
    }

    setFormSourceId("");
    setFormTargetId("");
    setFormType("upsell");
    setFormPriority("0");
    setDialogOpen(false);
    setCreating(false);
    fetchUpsells();
  }

  /**
   * Format the upsell type for display.
   *
   * @param type - The raw upsell type string.
   * @returns A human-readable label.
   */
  function formatType(type: Upsell["upsell_type"]): string {
    switch (type) {
      case "upsell":
        return "Upsell";
      case "cross_sell":
        return "Cross-sell";
      case "bundle":
        return "Bundle";
      default:
        return type;
    }
  }

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading upsells...</p>
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
          <h1 className="text-lg font-semibold">Upsells</h1>
        </div>

        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>Create Upsell</Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>New Upsell Rule</DialogTitle>
              <DialogDescription>
                Link two products together to suggest upgrades or
                complementary items during checkout.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              {createError && (
                <p className="text-sm text-destructive">{createError}</p>
              )}
              <div className="space-y-2">
                <Label htmlFor="upsell-source">Source Product ID</Label>
                <Input
                  id="upsell-source"
                  placeholder="Product being viewed..."
                  value={formSourceId}
                  onChange={(e) => setFormSourceId(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="upsell-target">Target Product ID</Label>
                <Input
                  id="upsell-target"
                  placeholder="Product to recommend..."
                  value={formTargetId}
                  onChange={(e) => setFormTargetId(e.target.value)}
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="upsell-type">Type</Label>
                  <Select
                    value={formType}
                    onValueChange={(v) =>
                      setFormType(v as "upsell" | "cross_sell" | "bundle")
                    }
                  >
                    <SelectTrigger id="upsell-type">
                      <SelectValue placeholder="Select type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="upsell">Upsell</SelectItem>
                      <SelectItem value="cross_sell">Cross-sell</SelectItem>
                      <SelectItem value="bundle">Bundle</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="upsell-priority">Priority</Label>
                  <Input
                    id="upsell-priority"
                    type="number"
                    min="0"
                    placeholder="0"
                    value={formPriority}
                    onChange={(e) => setFormPriority(e.target.value)}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={creating}>
                  {creating ? "Creating..." : "Create Upsell"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </header>

      <main className="p-6">
        {error && (
          <Card className="mb-6 border-destructive/50">
            <CardContent className="pt-6">
              <p className="text-sm text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {upsells.length === 0 ? (
          <div className="flex flex-col items-center gap-4 py-16 text-center">
            <div className="text-5xl opacity-20">&#8679;</div>
            <h2 className="text-xl font-semibold">No upsells configured</h2>
            <p className="text-muted-foreground max-w-sm">
              Create your first upsell rule to start recommending related
              products and increase average order value.
            </p>
            <Button onClick={() => setDialogOpen(true)}>
              Create your first upsell
            </Button>
          </div>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Upsell Rules</CardTitle>
              <CardDescription>
                {upsells.length} rule{upsells.length !== 1 ? "s" : ""} configured
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Source Product</TableHead>
                    <TableHead>Target Product</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Priority</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {upsells.map((upsell) => (
                    <TableRow key={upsell.id}>
                      <TableCell className="font-medium font-mono text-xs">
                        {upsell.source_product_id.slice(0, 8)}...
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {upsell.target_product_id.slice(0, 8)}...
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            upsell.upsell_type === "bundle"
                              ? "default"
                              : upsell.upsell_type === "cross_sell"
                                ? "secondary"
                                : "outline"
                          }
                        >
                          {formatType(upsell.upsell_type)}
                        </Badge>
                      </TableCell>
                      <TableCell>{upsell.position}</TableCell>
                      <TableCell>
                        <Badge
                          variant={upsell.is_active ? "default" : "secondary"}
                        >
                          {upsell.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
