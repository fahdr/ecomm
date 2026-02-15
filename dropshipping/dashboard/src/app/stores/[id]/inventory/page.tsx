/**
 * Inventory management page for ecommerce stores.
 *
 * Displays a stock overview with summary cards, an inventory levels table,
 * and provides dialogs for setting and adjusting stock levels. Filters
 * by warehouse and highlights low-stock items.
 *
 * **For Developers:**
 *   - Fetches data from ``/api/v1/stores/{store_id}/inventory/*`` endpoints.
 *   - Uses ``useStore()`` for the current store context.
 *   - Summary endpoint: ``GET /inventory/summary``.
 *   - Levels endpoint: ``GET /inventory`` with optional ``?warehouse_id=``.
 *   - Low-stock endpoint: ``GET /inventory/low-stock``.
 *   - Set level: ``POST /inventory`` with variant_id, warehouse_id, quantity.
 *   - Adjust: ``POST /inventory/{id}/adjust`` with quantity_change, reason.
 *   - Adjustments history: ``GET /inventory/{id}/adjustments``.
 *
 * **For QA Engineers:**
 *   - Summary cards show Total Stock, Reserved, Available, Low Stock Alerts.
 *   - Table columns: Product, Variant, Warehouse, Qty, Reserved, Available,
 *     Reorder Point, Actions.
 *   - "Set Inventory" dialog creates or updates a stock level.
 *   - "Adjust Stock" action per row opens an adjustment dialog.
 *   - Low-stock badge appears on items where ``is_low_stock`` is true.
 *   - Warehouse filter dropdown narrows the table to one warehouse.
 *
 * **For Project Managers:**
 *   Core inventory management dashboard for ecommerce mode. Enables
 *   merchants to track and manage stock across multiple warehouses
 *   with low-stock alerts and full audit trail.
 *
 * **For End Users:**
 *   View your product stock across all warehouses. Set stock levels,
 *   adjust quantities, and see which products are running low so you
 *   can reorder before they sell out.
 */

"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useAuth } from "@/contexts/auth-context";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import { PageTransition } from "@/components/motion-wrappers";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
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
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Boxes,
  Lock,
  PackageOpen,
  AlertTriangle,
  Plus,
  ArrowUpDown,
  History,
} from "lucide-react";

/** Warehouse response from the backend. */
interface Warehouse {
  id: string;
  store_id: string;
  name: string;
  is_default: boolean;
  is_active: boolean;
}

/** Inventory level response from the backend. */
interface InventoryLevel {
  id: string;
  variant_id: string;
  warehouse_id: string;
  quantity: number;
  reserved_quantity: number;
  available_quantity: number;
  reorder_point: number;
  reorder_quantity: number;
  is_low_stock: boolean;
  created_at: string;
  updated_at: string;
}

/** Inventory summary statistics. */
interface InventorySummary {
  total_warehouses: number;
  total_variants_tracked: number;
  total_in_stock: number;
  total_reserved: number;
  low_stock_count: number;
}

/** Adjustment history entry. */
interface InventoryAdjustment {
  id: string;
  inventory_level_id: string;
  quantity_change: number;
  reason: string;
  reference_id: string | null;
  notes: string | null;
  created_at: string;
}

/** Product variant for labeling inventory rows. */
interface ProductVariantInfo {
  id: string;
  name: string;
  sku: string | null;
  product_title: string;
}

/**
 * Inventory management page component.
 *
 * Renders summary cards, a filterable inventory levels table, and dialogs
 * for setting and adjusting stock. Fetches warehouses, levels, products,
 * and summary data from the API.
 *
 * @returns The rendered inventory management page.
 */
export default function InventoryPage() {
  const { store } = useStore();
  const storeId = store?.id;
  const { user, loading: authLoading } = useAuth();

  // Data state
  const [summary, setSummary] = useState<InventorySummary | null>(null);
  const [levels, setLevels] = useState<InventoryLevel[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [variantMap, setVariantMap] = useState<Record<string, ProductVariantInfo>>({});
  const [warehouseMap, setWarehouseMap] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  // Filter state
  const [filterWarehouse, setFilterWarehouse] = useState<string>("all");

  // Set Inventory dialog
  const [setDialogOpen, setSetDialogOpen] = useState(false);
  const [setVariantId, setSetVariantId] = useState("");
  const [setWarehouseId, setSetWarehouseId] = useState("");
  const [setQuantity, setSetQuantity] = useState("");
  const [setReorderPoint, setSetReorderPoint] = useState("");
  const [setReorderQty, setSetReorderQty] = useState("");
  const [setSaving, setSetSaving] = useState(false);
  const [setError, setSetError] = useState<string | null>(null);

  // Adjust dialog
  const [adjustDialogOpen, setAdjustDialogOpen] = useState(false);
  const [adjustLevelId, setAdjustLevelId] = useState("");
  const [adjustChange, setAdjustChange] = useState("");
  const [adjustReason, setAdjustReason] = useState("received");
  const [adjustNotes, setAdjustNotes] = useState("");
  const [adjustSaving, setAdjustSaving] = useState(false);
  const [adjustError, setAdjustError] = useState<string | null>(null);

  // Adjustment history
  const [historyDialogOpen, setHistoryDialogOpen] = useState(false);
  const [historyLevelId, setHistoryLevelId] = useState("");
  const [adjustments, setAdjustments] = useState<InventoryAdjustment[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  /**
   * Fetch all inventory data: summary, levels, warehouses, and product info.
   */
  const fetchData = useCallback(async () => {
    if (!storeId) return;
    setLoading(true);

    const warehouseFilter =
      filterWarehouse !== "all" ? `?warehouse_id=${filterWarehouse}` : "";

    const [summaryRes, levelsRes, whRes, productsRes] = await Promise.all([
      api.get<InventorySummary>(`/api/v1/stores/${storeId}/inventory/summary`),
      api.get<InventoryLevel[]>(`/api/v1/stores/${storeId}/inventory${warehouseFilter}`),
      api.get<Warehouse[]>(`/api/v1/stores/${storeId}/warehouses`),
      api.get<any>(`/api/v1/stores/${storeId}/products?per_page=200`),
    ]);

    if (summaryRes.data) setSummary(summaryRes.data);
    if (levelsRes.data) setLevels(Array.isArray(levelsRes.data) ? levelsRes.data : []);
    if (whRes.data) {
      const whs = Array.isArray(whRes.data) ? whRes.data : [];
      setWarehouses(whs);
      const wMap: Record<string, string> = {};
      for (const w of whs) wMap[w.id] = w.name;
      setWarehouseMap(wMap);
    }
    if (productsRes.data) {
      const products = Array.isArray(productsRes.data)
        ? productsRes.data
        : productsRes.data.items ?? [];
      const vMap: Record<string, ProductVariantInfo> = {};
      for (const p of products) {
        if (p.variants) {
          for (const v of p.variants) {
            vMap[v.id] = {
              id: v.id,
              name: v.name,
              sku: v.sku,
              product_title: p.title,
            };
          }
        }
      }
      setVariantMap(vMap);
    }
    setLoading(false);
  }, [storeId, filterWarehouse]);

  useEffect(() => {
    if (authLoading || !user) return;
    fetchData();
  }, [storeId, user, authLoading, fetchData]);

  /**
   * Handle the "Set Inventory" form submission.
   * @param e - Form submit event.
   */
  async function handleSetInventory(e: FormEvent) {
    e.preventDefault();
    setSetSaving(true);
    setSetError(null);

    const result = await api.post<InventoryLevel>(
      `/api/v1/stores/${storeId}/inventory`,
      {
        variant_id: setVariantId,
        warehouse_id: setWarehouseId,
        quantity: parseInt(setQuantity, 10) || 0,
        reorder_point: parseInt(setReorderPoint, 10) || 0,
        reorder_quantity: parseInt(setReorderQty, 10) || 0,
      }
    );

    if (result.error) {
      setSetError(result.error.message);
      setSetSaving(false);
      return;
    }

    setSetDialogOpen(false);
    resetSetForm();
    setSetSaving(false);
    fetchData();
  }

  /**
   * Reset the "Set Inventory" form fields.
   */
  function resetSetForm() {
    setSetVariantId("");
    setSetWarehouseId("");
    setSetQuantity("");
    setSetReorderPoint("");
    setSetReorderQty("");
    setSetError(null);
  }

  /**
   * Handle the "Adjust Stock" form submission.
   * @param e - Form submit event.
   */
  async function handleAdjust(e: FormEvent) {
    e.preventDefault();
    setAdjustSaving(true);
    setAdjustError(null);

    const result = await api.post<InventoryLevel>(
      `/api/v1/stores/${storeId}/inventory/${adjustLevelId}/adjust`,
      {
        quantity_change: parseInt(adjustChange, 10) || 0,
        reason: adjustReason,
        notes: adjustNotes || null,
      }
    );

    if (result.error) {
      setAdjustError(result.error.message);
      setAdjustSaving(false);
      return;
    }

    setAdjustDialogOpen(false);
    resetAdjustForm();
    setAdjustSaving(false);
    fetchData();
  }

  /**
   * Reset the "Adjust Stock" form fields.
   */
  function resetAdjustForm() {
    setAdjustLevelId("");
    setAdjustChange("");
    setAdjustReason("received");
    setAdjustNotes("");
    setAdjustError(null);
  }

  /**
   * Open the adjustment dialog pre-filled for a specific inventory level.
   * @param levelId - The inventory level ID to adjust.
   */
  function openAdjustDialog(levelId: string) {
    setAdjustLevelId(levelId);
    setAdjustDialogOpen(true);
  }

  /**
   * Open the adjustment history dialog for a specific inventory level.
   * @param levelId - The inventory level ID.
   */
  async function openHistoryDialog(levelId: string) {
    setHistoryLevelId(levelId);
    setHistoryDialogOpen(true);
    setHistoryLoading(true);

    const res = await api.get<InventoryAdjustment[]>(
      `/api/v1/stores/${storeId}/inventory/${levelId}/adjustments`
    );
    if (res.data) {
      setAdjustments(Array.isArray(res.data) ? res.data : []);
    }
    setHistoryLoading(false);
  }

  /** Adjustment reason options for the select dropdown. */
  const REASONS = [
    { value: "received", label: "Received" },
    { value: "sold", label: "Sold" },
    { value: "returned", label: "Returned" },
    { value: "damaged", label: "Damaged" },
    { value: "correction", label: "Correction" },
    { value: "reserved", label: "Reserved" },
    { value: "unreserved", label: "Unreserved" },
    { value: "transfer", label: "Transfer" },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-foreground/20 border-t-foreground" />
          <p className="text-sm text-muted-foreground tracking-wide">
            Loading inventory...
          </p>
        </div>
      </div>
    );
  }

  return (
    <PageTransition>
      <main className="mx-auto max-w-5xl p-6 space-y-6">
        {/* Page heading */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold font-heading">Inventory</h1>
          <Button
            onClick={() => {
              resetSetForm();
              setSetDialogOpen(true);
            }}
            className="gap-1.5"
          >
            <Plus className="h-4 w-4" />
            Set Inventory
          </Button>
        </div>

        {/* Summary cards */}
        {summary && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <Boxes className="h-4 w-4 text-teal-500" />
                  Total Stock
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold tabular-nums">
                  {summary.total_in_stock.toLocaleString()}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  across {summary.total_warehouses} warehouse{summary.total_warehouses !== 1 ? "s" : ""}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <Lock className="h-4 w-4 text-blue-500" />
                  Reserved
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold tabular-nums">
                  {summary.total_reserved.toLocaleString()}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  for pending orders
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <PackageOpen className="h-4 w-4 text-emerald-500" />
                  Available
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold tabular-nums text-emerald-600">
                  {(summary.total_in_stock - summary.total_reserved).toLocaleString()}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  ready to ship
                </p>
              </CardContent>
            </Card>

            <Card className={summary.low_stock_count > 0 ? "border-amber-400/60" : ""}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <AlertTriangle className={`h-4 w-4 ${summary.low_stock_count > 0 ? "text-amber-500" : "text-muted-foreground"}`} />
                  Low Stock Alerts
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className={`text-2xl font-bold tabular-nums ${summary.low_stock_count > 0 ? "text-amber-600" : ""}`}>
                  {summary.low_stock_count}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  items below reorder point
                </p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Warehouse filter */}
        <div className="flex items-center gap-3">
          <Label htmlFor="wh-filter" className="text-sm font-medium whitespace-nowrap">
            Filter by warehouse
          </Label>
          <Select value={filterWarehouse} onValueChange={setFilterWarehouse}>
            <SelectTrigger id="wh-filter" className="w-56">
              <SelectValue placeholder="All warehouses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All warehouses</SelectItem>
              {warehouses.map((wh) => (
                <SelectItem key={wh.id} value={wh.id}>
                  {wh.name}{wh.is_default ? " (Default)" : ""}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Inventory levels table */}
        {levels.length === 0 ? (
          <div className="flex flex-col items-center gap-4 py-16 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
              <Boxes className="h-8 w-8 text-muted-foreground" />
            </div>
            <h2 className="text-xl font-semibold font-heading">No inventory tracked yet</h2>
            <p className="max-w-sm text-muted-foreground">
              Set inventory levels for your product variants to start tracking
              stock across your warehouses.
            </p>
            <Button
              onClick={() => {
                resetSetForm();
                setSetDialogOpen(true);
              }}
            >
              Set your first inventory level
            </Button>
          </div>
        ) : (
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="pl-4">Product</TableHead>
                    <TableHead>Variant</TableHead>
                    <TableHead>Warehouse</TableHead>
                    <TableHead className="text-right">Qty</TableHead>
                    <TableHead className="text-right">Reserved</TableHead>
                    <TableHead className="text-right">Available</TableHead>
                    <TableHead className="text-right">Reorder Pt</TableHead>
                    <TableHead className="pr-4 text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {levels.map((level) => {
                    const vInfo = variantMap[level.variant_id];
                    return (
                      <TableRow key={level.id}>
                        <TableCell className="pl-4">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-sm truncate max-w-[200px]">
                              {vInfo?.product_title || "Unknown Product"}
                            </span>
                            {level.is_low_stock && (
                              <Badge
                                variant="secondary"
                                className="bg-amber-100 text-amber-800 border-amber-300 text-[10px] px-1.5 py-0"
                              >
                                Low Stock
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div>
                            <span className="text-sm">{vInfo?.name || "---"}</span>
                            {vInfo?.sku && (
                              <p className="text-xs text-muted-foreground">
                                SKU: {vInfo.sku}
                              </p>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-sm">
                          {warehouseMap[level.warehouse_id] || "---"}
                        </TableCell>
                        <TableCell className="text-right tabular-nums font-semibold">
                          {level.quantity}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {level.reserved_quantity}
                        </TableCell>
                        <TableCell className="text-right tabular-nums font-semibold text-emerald-600">
                          {level.available_quantity}
                        </TableCell>
                        <TableCell className="text-right tabular-nums text-muted-foreground">
                          {level.reorder_point > 0 ? level.reorder_point : "\u2014"}
                        </TableCell>
                        <TableCell className="pr-4 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 px-2 text-xs gap-1"
                              onClick={() => openAdjustDialog(level.id)}
                              title="Adjust stock"
                            >
                              <ArrowUpDown className="h-3 w-3" />
                              Adjust
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 px-2 text-xs gap-1"
                              onClick={() => openHistoryDialog(level.id)}
                              title="View history"
                            >
                              <History className="h-3 w-3" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        {/* Set Inventory Dialog */}
        <Dialog
          open={setDialogOpen}
          onOpenChange={(open) => {
            setSetDialogOpen(open);
            if (!open) resetSetForm();
          }}
        >
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Set Inventory Level</DialogTitle>
              <DialogDescription>
                Set the stock quantity for a product variant at a specific warehouse.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSetInventory}>
              <div className="space-y-4 py-4">
                {setError && (
                  <p className="text-sm text-destructive">{setError}</p>
                )}
                <div className="space-y-2">
                  <Label htmlFor="set-variant">Product Variant</Label>
                  <Select value={setVariantId} onValueChange={setSetVariantId}>
                    <SelectTrigger id="set-variant">
                      <SelectValue placeholder="Select a variant" />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(variantMap).map(([vid, info]) => (
                        <SelectItem key={vid} value={vid}>
                          {info.product_title} - {info.name}
                          {info.sku ? ` (${info.sku})` : ""}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="set-warehouse">Warehouse</Label>
                  <Select value={setWarehouseId} onValueChange={setSetWarehouseId}>
                    <SelectTrigger id="set-warehouse">
                      <SelectValue placeholder="Select a warehouse" />
                    </SelectTrigger>
                    <SelectContent>
                      {warehouses.map((wh) => (
                        <SelectItem key={wh.id} value={wh.id}>
                          {wh.name}{wh.is_default ? " (Default)" : ""}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div className="space-y-2">
                    <Label htmlFor="set-qty">Quantity</Label>
                    <Input
                      id="set-qty"
                      type="number"
                      min="0"
                      placeholder="0"
                      value={setQuantity}
                      onChange={(e) => setSetQuantity(e.target.value)}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="set-reorder-pt">Reorder Point</Label>
                    <Input
                      id="set-reorder-pt"
                      type="number"
                      min="0"
                      placeholder="0"
                      value={setReorderPoint}
                      onChange={(e) => setSetReorderPoint(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="set-reorder-qty">Reorder Qty</Label>
                    <Input
                      id="set-reorder-qty"
                      type="number"
                      min="0"
                      placeholder="0"
                      value={setReorderQty}
                      onChange={(e) => setSetReorderQty(e.target.value)}
                    />
                  </div>
                </div>
              </div>
              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setSetDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={setSaving || !setVariantId || !setWarehouseId}>
                  {setSaving ? "Setting..." : "Set Level"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Adjust Stock Dialog */}
        <Dialog
          open={adjustDialogOpen}
          onOpenChange={(open) => {
            setAdjustDialogOpen(open);
            if (!open) resetAdjustForm();
          }}
        >
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Adjust Stock</DialogTitle>
              <DialogDescription>
                Add or remove stock. Use positive numbers to add, negative to remove.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleAdjust}>
              <div className="space-y-4 py-4">
                {adjustError && (
                  <p className="text-sm text-destructive">{adjustError}</p>
                )}
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label htmlFor="adj-change">Quantity Change</Label>
                    <Input
                      id="adj-change"
                      type="number"
                      placeholder="+10 or -5"
                      value={adjustChange}
                      onChange={(e) => setAdjustChange(e.target.value)}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="adj-reason">Reason</Label>
                    <Select value={adjustReason} onValueChange={setAdjustReason}>
                      <SelectTrigger id="adj-reason">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {REASONS.map((r) => (
                          <SelectItem key={r.value} value={r.value}>
                            {r.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="adj-notes">Notes (optional)</Label>
                  <Input
                    id="adj-notes"
                    placeholder="Reason for adjustment..."
                    value={adjustNotes}
                    onChange={(e) => setAdjustNotes(e.target.value)}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setAdjustDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={adjustSaving || !adjustChange}>
                  {adjustSaving ? "Adjusting..." : "Apply Adjustment"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Adjustment History Dialog */}
        <Dialog
          open={historyDialogOpen}
          onOpenChange={setHistoryDialogOpen}
        >
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle>Adjustment History</DialogTitle>
              <DialogDescription>
                Audit trail of all stock changes for this inventory level.
              </DialogDescription>
            </DialogHeader>
            <div className="max-h-80 overflow-y-auto">
              {historyLoading ? (
                <div className="flex justify-center py-8">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-foreground/20 border-t-foreground" />
                </div>
              ) : adjustments.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No adjustments recorded yet.
                </p>
              ) : (
                <div className="space-y-2">
                  {adjustments.map((adj) => (
                    <div
                      key={adj.id}
                      className="flex items-center justify-between p-3 rounded-lg border border-border"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <Badge
                            variant="secondary"
                            className={
                              adj.quantity_change > 0
                                ? "bg-emerald-100 text-emerald-800"
                                : "bg-red-100 text-red-800"
                            }
                          >
                            {adj.quantity_change > 0 ? "+" : ""}
                            {adj.quantity_change}
                          </Badge>
                          <span className="text-sm font-medium capitalize">
                            {adj.reason}
                          </span>
                        </div>
                        {adj.notes && (
                          <p className="text-xs text-muted-foreground mt-1">
                            {adj.notes}
                          </p>
                        )}
                      </div>
                      <span className="text-xs text-muted-foreground whitespace-nowrap">
                        {new Date(adj.created_at).toLocaleString()}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      </main>
    </PageTransition>
  );
}
