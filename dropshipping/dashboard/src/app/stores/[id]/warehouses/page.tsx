/**
 * Warehouses management page for ecommerce stores.
 *
 * Lists all warehouses with their location details, default/active status,
 * and provides dialogs for creating, editing, and deleting warehouses.
 *
 * **For Developers:**
 *   - Fetches from ``GET /api/v1/stores/{store_id}/warehouses``.
 *   - Create: ``POST /api/v1/stores/{store_id}/warehouses``.
 *   - Update: ``PATCH /api/v1/stores/{store_id}/warehouses/{id}``.
 *   - Delete: ``DELETE /api/v1/stores/{store_id}/warehouses/{id}``.
 *   - Setting ``is_default: true`` unsets the previous default on the backend.
 *   - Deleting the default warehouse returns 400.
 *
 * **For QA Engineers:**
 *   - Warehouses list shows name, location, default badge, active status.
 *   - "Add Warehouse" dialog includes name, address, city, state, country, zip.
 *   - Edit dialog pre-fills existing data.
 *   - Delete requires confirmation and fails for default warehouses.
 *   - "Set as Default" action is available for non-default warehouses.
 *
 * **For Project Managers:**
 *   Warehouse management enables multi-location fulfillment for ecommerce
 *   mode. One warehouse is always marked as default for new inventory entries.
 *
 * **For End Users:**
 *   Manage your warehouse locations. Add warehouses for different fulfillment
 *   centers, set a default warehouse, and remove locations you no longer use.
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Warehouse as WarehouseIcon,
  Plus,
  MapPin,
  Star,
  Trash2,
  Pencil,
} from "lucide-react";

/** Warehouse response from the backend API. */
interface Warehouse {
  id: string;
  store_id: string;
  name: string;
  address: string | null;
  city: string | null;
  state: string | null;
  country: string;
  zip_code: string | null;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/**
 * Format a warehouse location into a human-readable string.
 *
 * @param wh - The warehouse object.
 * @returns Formatted location string (e.g. "Houston, TX, US 77001").
 */
function formatLocation(wh: Warehouse): string {
  const parts: string[] = [];
  if (wh.city) parts.push(wh.city);
  if (wh.state) parts.push(wh.state);
  if (wh.country) parts.push(wh.country);
  if (wh.zip_code) parts.push(wh.zip_code);
  return parts.join(", ") || "\u2014";
}

/**
 * Warehouses management page component.
 *
 * Fetches and displays all warehouses for the current store. Provides
 * create, edit, delete, and set-default actions via dialog forms.
 *
 * @returns The rendered warehouses management page.
 */
export default function WarehousesPage() {
  const { store } = useStore();
  const storeId = store?.id;
  const { user, loading: authLoading } = useAuth();

  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dialog state (shared for create/edit)
  const [dialogOpen, setDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [editingWarehouse, setEditingWarehouse] = useState<Warehouse | null>(null);

  // Form fields
  const [formName, setFormName] = useState("");
  const [formAddress, setFormAddress] = useState("");
  const [formCity, setFormCity] = useState("");
  const [formState, setFormState] = useState("");
  const [formCountry, setFormCountry] = useState("US");
  const [formZip, setFormZip] = useState("");

  // Delete state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingWarehouse, setDeletingWarehouse] = useState<Warehouse | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  /**
   * Fetch all warehouses for the store.
   */
  const fetchWarehouses = useCallback(async () => {
    if (!storeId) return;
    setLoading(true);
    const result = await api.get<Warehouse[]>(
      `/api/v1/stores/${storeId}/warehouses`
    );
    if (result.data) {
      setWarehouses(Array.isArray(result.data) ? result.data : []);
      setError(null);
    } else {
      setError(result.error?.message || "Failed to load warehouses");
    }
    setLoading(false);
  }, [storeId]);

  useEffect(() => {
    if (authLoading || !user) return;
    fetchWarehouses();
  }, [storeId, user, authLoading, fetchWarehouses]);

  /**
   * Reset form to blank state for creating a new warehouse.
   */
  function resetForm() {
    setEditingWarehouse(null);
    setFormName("");
    setFormAddress("");
    setFormCity("");
    setFormState("");
    setFormCountry("US");
    setFormZip("");
    setSaveError(null);
  }

  /**
   * Populate the form with an existing warehouse for editing.
   * @param wh - The warehouse to edit.
   */
  function openEditDialog(wh: Warehouse) {
    setEditingWarehouse(wh);
    setFormName(wh.name);
    setFormAddress(wh.address || "");
    setFormCity(wh.city || "");
    setFormState(wh.state || "");
    setFormCountry(wh.country);
    setFormZip(wh.zip_code || "");
    setSaveError(null);
    setDialogOpen(true);
  }

  /**
   * Handle form submission for both create and edit operations.
   * @param e - The form submission event.
   */
  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaveError(null);

    const payload = {
      name: formName.trim(),
      address: formAddress.trim() || null,
      city: formCity.trim() || null,
      state: formState.trim() || null,
      country: formCountry.trim() || "US",
      zip_code: formZip.trim() || null,
    };

    let result;
    if (editingWarehouse) {
      result = await api.patch<Warehouse>(
        `/api/v1/stores/${storeId}/warehouses/${editingWarehouse.id}`,
        payload
      );
    } else {
      result = await api.post<Warehouse>(
        `/api/v1/stores/${storeId}/warehouses`,
        payload
      );
    }

    if (result.error) {
      setSaveError(result.error.message);
      setSaving(false);
      return;
    }

    setDialogOpen(false);
    resetForm();
    setSaving(false);
    fetchWarehouses();
  }

  /**
   * Set a warehouse as the default.
   * @param wh - The warehouse to set as default.
   */
  async function handleSetDefault(wh: Warehouse) {
    await api.patch<Warehouse>(
      `/api/v1/stores/${storeId}/warehouses/${wh.id}`,
      { is_default: true }
    );
    fetchWarehouses();
  }

  /**
   * Open the delete confirmation dialog.
   * @param wh - The warehouse to delete.
   */
  function openDeleteDialog(wh: Warehouse) {
    setDeletingWarehouse(wh);
    setDeleteError(null);
    setDeleteDialogOpen(true);
  }

  /**
   * Confirm and execute warehouse deletion.
   */
  async function handleDelete() {
    if (!deletingWarehouse) return;
    setDeleting(true);
    setDeleteError(null);

    const result = await api.delete(
      `/api/v1/stores/${storeId}/warehouses/${deletingWarehouse.id}`
    );

    if (result.error) {
      setDeleteError(result.error.message);
      setDeleting(false);
      return;
    }

    setDeleteDialogOpen(false);
    setDeletingWarehouse(null);
    setDeleting(false);
    fetchWarehouses();
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-foreground/20 border-t-foreground" />
          <p className="text-sm text-muted-foreground tracking-wide">
            Loading warehouses...
          </p>
        </div>
      </div>
    );
  }

  return (
    <PageTransition>
      <main className="mx-auto max-w-4xl p-6 space-y-6">
        {/* Page heading and action */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold font-heading">Warehouses</h1>
          <Button
            onClick={() => {
              resetForm();
              setDialogOpen(true);
            }}
            className="gap-1.5"
          >
            <Plus className="h-4 w-4" />
            Add Warehouse
          </Button>
        </div>

        {error && (
          <Card className="border-destructive/50">
            <CardContent className="pt-6">
              <p className="text-sm text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* Summary cards */}
        <div className="grid gap-4 sm:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Warehouses
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold tabular-nums">{warehouses.length}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Active
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold tabular-nums text-emerald-600">
                {warehouses.filter((w) => w.is_active).length}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Countries
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold tabular-nums">
                {new Set(warehouses.map((w) => w.country)).size}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Warehouses table */}
        {warehouses.length === 0 ? (
          <div className="flex flex-col items-center gap-4 py-16 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
              <WarehouseIcon className="h-8 w-8 text-muted-foreground" />
            </div>
            <h2 className="text-xl font-semibold font-heading">No warehouses yet</h2>
            <p className="max-w-sm text-muted-foreground">
              Add your first warehouse to start managing inventory across
              multiple fulfillment locations.
            </p>
            <Button
              onClick={() => {
                resetForm();
                setDialogOpen(true);
              }}
            >
              Add your first warehouse
            </Button>
          </div>
        ) : (
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="pl-4">Name</TableHead>
                    <TableHead>Location</TableHead>
                    <TableHead>Address</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="pr-4 text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {warehouses.map((wh) => (
                    <TableRow key={wh.id}>
                      <TableCell className="pl-4">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold">{wh.name}</span>
                          {wh.is_default && (
                            <Badge
                              variant="secondary"
                              className="bg-teal-100 text-teal-800 border-teal-300 text-[10px] px-1.5 py-0"
                            >
                              Default
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1.5 text-sm">
                          <MapPin className="h-3 w-3 text-muted-foreground shrink-0" />
                          {formatLocation(wh)}
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground truncate max-w-[200px]">
                        {wh.address || "\u2014"}
                      </TableCell>
                      <TableCell>
                        <Badge variant={wh.is_active ? "default" : "secondary"}>
                          {wh.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                      <TableCell className="pr-4 text-right">
                        <div className="flex items-center justify-end gap-1">
                          {!wh.is_default && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 px-2 text-xs gap-1"
                              onClick={() => handleSetDefault(wh)}
                              title="Set as default"
                            >
                              <Star className="h-3 w-3" />
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2 text-xs gap-1"
                            onClick={() => openEditDialog(wh)}
                            title="Edit warehouse"
                          >
                            <Pencil className="h-3 w-3" />
                            Edit
                          </Button>
                          {!wh.is_default && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 px-2 text-xs gap-1 text-destructive hover:text-destructive"
                              onClick={() => openDeleteDialog(wh)}
                              title="Delete warehouse"
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        {/* Create/Edit Warehouse Dialog */}
        <Dialog
          open={dialogOpen}
          onOpenChange={(open) => {
            setDialogOpen(open);
            if (!open) resetForm();
          }}
        >
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle>
                {editingWarehouse ? "Edit Warehouse" : "Add Warehouse"}
              </DialogTitle>
              <DialogDescription>
                {editingWarehouse
                  ? `Update details for "${editingWarehouse.name}".`
                  : "Add a new warehouse or fulfillment location."}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit}>
              <div className="space-y-4 py-4">
                {saveError && (
                  <p className="text-sm text-destructive">{saveError}</p>
                )}
                <div className="space-y-2">
                  <Label htmlFor="wh-name">Warehouse Name</Label>
                  <Input
                    id="wh-name"
                    placeholder="e.g. East Coast Fulfillment"
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    required
                    maxLength={255}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="wh-address">Street Address</Label>
                  <Input
                    id="wh-address"
                    placeholder="123 Warehouse Blvd"
                    value={formAddress}
                    onChange={(e) => setFormAddress(e.target.value)}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="wh-city">City</Label>
                    <Input
                      id="wh-city"
                      placeholder="Houston"
                      value={formCity}
                      onChange={(e) => setFormCity(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="wh-state">State / Province</Label>
                    <Input
                      id="wh-state"
                      placeholder="TX"
                      value={formState}
                      onChange={(e) => setFormState(e.target.value)}
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="wh-country">Country Code</Label>
                    <Input
                      id="wh-country"
                      placeholder="US"
                      value={formCountry}
                      onChange={(e) => setFormCountry(e.target.value)}
                      maxLength={2}
                      minLength={2}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="wh-zip">ZIP / Postal Code</Label>
                    <Input
                      id="wh-zip"
                      placeholder="77001"
                      value={formZip}
                      onChange={(e) => setFormZip(e.target.value)}
                    />
                  </div>
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
                <Button type="submit" disabled={saving}>
                  {saving
                    ? editingWarehouse
                      ? "Saving..."
                      : "Adding..."
                    : editingWarehouse
                      ? "Save Changes"
                      : "Add Warehouse"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                Delete &quot;{deletingWarehouse?.name}&quot;?
              </DialogTitle>
              <DialogDescription>
                This will permanently remove the warehouse and all its inventory
                levels. This action cannot be undone.
              </DialogDescription>
            </DialogHeader>
            {deleteError && (
              <p className="text-sm text-destructive">{deleteError}</p>
            )}
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
                {deleting ? "Deleting..." : "Delete Warehouse"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </main>
    </PageTransition>
  );
}
