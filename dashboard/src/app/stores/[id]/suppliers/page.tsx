/**
 * Suppliers management page for a store.
 *
 * Lists all suppliers in a data table showing name, contact, reliability
 * rating, average shipping days, and status. Provides dialog forms to
 * create and edit supplier profiles.
 *
 * **For End Users:**
 *   Track your suppliers' performance, shipping times, and contact info
 *   in one place. Reliability scores help you decide which suppliers to
 *   prioritize for new products.
 *
 * **For QA Engineers:**
 *   - Suppliers load from ``GET /api/v1/stores/{store_id}/suppliers``.
 *   - Creating calls ``POST /api/v1/stores/{store_id}/suppliers``.
 *   - Editing calls ``PATCH /api/v1/stores/{store_id}/suppliers/{id}``.
 *   - Reliability is displayed as a percentage bar (0-100).
 *   - Shipping days shows average and max values.
 *
 * **For Developers:**
 *   - Follows the store sub-page pattern with breadcrumb header.
 *   - Uses a single dialog component for both create and edit flows,
 *     differentiated by the ``editingSupplier`` state.
 *
 * **For Project Managers:**
 *   Implements Feature 10 (Supplier Management) from the backlog. Covers
 *   the CRUD interface; supplier order integration comes with Feature 10b.
 */

"use client";

import { FormEvent, useEffect, useState, use, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
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

/** Shape of a supplier returned by the backend API. */
interface Supplier {
  id: string;
  name: string;
  contact_email: string | null;
  contact_phone: string | null;
  website: string | null;
  status: "active" | "inactive" | "blocked";
  reliability_score: number;
  avg_shipping_days: number;
  max_shipping_days: number;
  notes: string | null;
  product_count: number;
  created_at: string;
}

/**
 * Get a badge variant for supplier status.
 * @param status - The supplier's current status.
 * @returns Badge variant string.
 */
function supplierStatusVariant(
  status: Supplier["status"]
): "default" | "secondary" | "destructive" {
  switch (status) {
    case "active":
      return "default";
    case "inactive":
      return "secondary";
    case "blocked":
      return "destructive";
    default:
      return "secondary";
  }
}

/**
 * Render a reliability score as a colored indicator.
 * @param score - Reliability percentage (0-100).
 * @returns A CSS color class name.
 */
function reliabilityColor(score: number): string {
  if (score >= 90) return "text-emerald-600";
  if (score >= 70) return "text-amber-600";
  return "text-red-600";
}

export default function SuppliersPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: storeId } = use(params);
  const { user, loading: authLoading } = useAuth();

  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dialog state (shared for create/edit).
  const [dialogOpen, setDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [editingSupplier, setEditingSupplier] = useState<Supplier | null>(null);

  // Form fields.
  const [formName, setFormName] = useState("");
  const [formEmail, setFormEmail] = useState("");
  const [formPhone, setFormPhone] = useState("");
  const [formWebsite, setFormWebsite] = useState("");
  const [formStatus, setFormStatus] = useState<Supplier["status"]>("active");
  const [formShippingDays, setFormShippingDays] = useState("");
  const [formMaxShippingDays, setFormMaxShippingDays] = useState("");
  const [formNotes, setFormNotes] = useState("");

  /**
   * Fetch all suppliers for this store from the backend.
   */
  const fetchSuppliers = useCallback(async () => {
    setLoading(true);
    const result = await api.get<{ items: Supplier[]; total: number }>(
      `/api/v1/stores/${storeId}/suppliers`
    );
    if (result.data) {
      setSuppliers(result.data.items ?? []);
      setError(null);
    } else {
      setError(result.error?.message || "Failed to load suppliers");
    }
    setLoading(false);
  }, [storeId]);

  useEffect(() => {
    if (authLoading || !user) return;
    fetchSuppliers();
  }, [storeId, user, authLoading, fetchSuppliers]);

  /**
   * Reset the form to a clean state for creating a new supplier.
   */
  function resetForm() {
    setEditingSupplier(null);
    setFormName("");
    setFormEmail("");
    setFormPhone("");
    setFormWebsite("");
    setFormStatus("active");
    setFormShippingDays("");
    setFormMaxShippingDays("");
    setFormNotes("");
    setSaveError(null);
  }

  /**
   * Populate the form with an existing supplier's data for editing.
   * @param supplier - The supplier to edit.
   */
  function openEditDialog(supplier: Supplier) {
    setEditingSupplier(supplier);
    setFormName(supplier.name);
    setFormEmail(supplier.contact_email || "");
    setFormPhone(supplier.contact_phone || "");
    setFormWebsite(supplier.website || "");
    setFormStatus(supplier.status);
    setFormShippingDays(String(supplier.avg_shipping_days));
    setFormMaxShippingDays(String(supplier.max_shipping_days));
    setFormNotes(supplier.notes || "");
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
      contact_email: formEmail.trim() || null,
      contact_phone: formPhone.trim() || null,
      website: formWebsite.trim() || null,
      status: formStatus,
      avg_shipping_days: parseInt(formShippingDays, 10) || 7,
      max_shipping_days: parseInt(formMaxShippingDays, 10) || 14,
      notes: formNotes.trim() || null,
    };

    let result;
    if (editingSupplier) {
      result = await api.patch<Supplier>(
        `/api/v1/stores/${storeId}/suppliers/${editingSupplier.id}`,
        payload
      );
    } else {
      result = await api.post<Supplier>(
        `/api/v1/stores/${storeId}/suppliers`,
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
    fetchSuppliers();
  }

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-foreground/20 border-t-foreground" />
          <p className="text-sm text-muted-foreground tracking-wide">Loading suppliers...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Breadcrumb header */}
      <header className="flex items-center justify-between border-b px-6 py-4">
        <div className="flex items-center gap-4">
          <Link href="/stores" className="text-lg font-semibold hover:underline">
            Stores
          </Link>
          <span className="text-muted-foreground">/</span>
          <Link
            href={`/stores/${storeId}`}
            className="text-lg font-semibold hover:underline"
          >
            Store
          </Link>
          <span className="text-muted-foreground">/</span>
          <h1 className="text-lg font-semibold">Suppliers</h1>
        </div>
        <Button
          onClick={() => {
            resetForm();
            setDialogOpen(true);
          }}
        >
          Add Supplier
        </Button>
      </header>

      <main className="p-6">
        {error && (
          <Card className="mb-6 border-destructive/50">
            <CardContent className="pt-6">
              <p className="text-sm text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* Summary cards */}
        <div className="mb-6 grid gap-4 sm:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Suppliers
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold tabular-nums">{suppliers.length}</p>
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
                {suppliers.filter((s) => s.status === "active").length}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Avg Reliability
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold tabular-nums">
                {suppliers.length > 0
                  ? `${Math.round(suppliers.reduce((s, sup) => s + sup.reliability_score, 0) / suppliers.length)}%`
                  : "\u2014"}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Avg Shipping
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold tabular-nums">
                {suppliers.length > 0
                  ? `${Math.round(suppliers.reduce((s, sup) => s + sup.avg_shipping_days, 0) / suppliers.length)}d`
                  : "\u2014"}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Suppliers table */}
        {suppliers.length === 0 ? (
          <div className="flex flex-col items-center gap-4 py-16 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
              <span className="text-2xl text-muted-foreground">S</span>
            </div>
            <h2 className="text-xl font-semibold">No suppliers yet</h2>
            <p className="max-w-sm text-muted-foreground">
              Add your suppliers to track their reliability, shipping times,
              and manage your supply chain effectively.
            </p>
            <Button onClick={() => { resetForm(); setDialogOpen(true); }}>
              Add your first supplier
            </Button>
          </div>
        ) : (
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="pl-4">Name</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Reliability</TableHead>
                    <TableHead>Shipping (avg / max)</TableHead>
                    <TableHead>Products</TableHead>
                    <TableHead>Contact</TableHead>
                    <TableHead className="pr-4">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {suppliers.map((supplier) => (
                    <TableRow key={supplier.id}>
                      <TableCell className="pl-4">
                        <div>
                          <p className="font-semibold">{supplier.name}</p>
                          {supplier.website && (
                            <p className="text-xs text-muted-foreground truncate max-w-[200px]">
                              {supplier.website}
                            </p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={supplierStatusVariant(supplier.status)}>
                          {supplier.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="h-2 w-16 rounded-full bg-muted overflow-hidden">
                            <div
                              className="h-full rounded-full bg-current transition-all"
                              style={{ width: `${supplier.reliability_score}%` }}
                            />
                          </div>
                          <span className={`text-sm font-semibold tabular-nums ${reliabilityColor(supplier.reliability_score)}`}>
                            {supplier.reliability_score}%
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="tabular-nums">
                        {supplier.avg_shipping_days}d / {supplier.max_shipping_days}d
                      </TableCell>
                      <TableCell className="tabular-nums">
                        {supplier.product_count}
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          {supplier.contact_email && (
                            <p className="truncate max-w-[180px]">{supplier.contact_email}</p>
                          )}
                          {supplier.contact_phone && (
                            <p className="text-muted-foreground">{supplier.contact_phone}</p>
                          )}
                          {!supplier.contact_email && !supplier.contact_phone && (
                            <span className="text-muted-foreground">\u2014</span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="pr-4">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => openEditDialog(supplier)}
                        >
                          Edit
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </main>

      {/* Create/Edit Supplier Dialog */}
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
              {editingSupplier ? "Edit Supplier" : "Add Supplier"}
            </DialogTitle>
            <DialogDescription>
              {editingSupplier
                ? `Update details for "${editingSupplier.name}".`
                : "Add a new supplier to your network."}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="space-y-4 py-4">
              {saveError && (
                <p className="text-sm text-destructive">{saveError}</p>
              )}
              <div className="space-y-2">
                <Label htmlFor="supplier-name">Supplier Name</Label>
                <Input
                  id="supplier-name"
                  placeholder="e.g. AliExpress Store #42"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="supplier-email">Email</Label>
                  <Input
                    id="supplier-email"
                    type="email"
                    placeholder="supplier@example.com"
                    value={formEmail}
                    onChange={(e) => setFormEmail(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="supplier-phone">Phone</Label>
                  <Input
                    id="supplier-phone"
                    placeholder="+1 (555) 000-0000"
                    value={formPhone}
                    onChange={(e) => setFormPhone(e.target.value)}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="supplier-website">Website</Label>
                <Input
                  id="supplier-website"
                  type="url"
                  placeholder="https://supplier.example.com"
                  value={formWebsite}
                  onChange={(e) => setFormWebsite(e.target.value)}
                />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="supplier-status">Status</Label>
                  <Select
                    value={formStatus}
                    onValueChange={(v) => setFormStatus(v as Supplier["status"])}
                  >
                    <SelectTrigger id="supplier-status">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="active">Active</SelectItem>
                      <SelectItem value="inactive">Inactive</SelectItem>
                      <SelectItem value="blocked">Blocked</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="avg-shipping">Avg Shipping (days)</Label>
                  <Input
                    id="avg-shipping"
                    type="number"
                    min="1"
                    placeholder="7"
                    value={formShippingDays}
                    onChange={(e) => setFormShippingDays(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="max-shipping">Max Shipping (days)</Label>
                  <Input
                    id="max-shipping"
                    type="number"
                    min="1"
                    placeholder="14"
                    value={formMaxShippingDays}
                    onChange={(e) => setFormMaxShippingDays(e.target.value)}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="supplier-notes">Notes</Label>
                <Textarea
                  id="supplier-notes"
                  placeholder="Internal notes about this supplier..."
                  value={formNotes}
                  onChange={(e) => setFormNotes(e.target.value)}
                  rows={3}
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
              <Button type="submit" disabled={saving}>
                {saving
                  ? editingSupplier
                    ? "Saving..."
                    : "Adding..."
                  : editingSupplier
                    ? "Save Changes"
                    : "Add Supplier"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
