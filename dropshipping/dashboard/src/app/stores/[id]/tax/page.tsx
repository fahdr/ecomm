/**
 * Tax Rates management page.
 *
 * Lists all tax rates configured for a store and provides a form to
 * create new tax rate entries. Each tax rate specifies a name, percentage
 * rate, country, optional state/province, and active status.
 *
 * **For End Users:**
 *   Manage your store's tax configuration by adding rates for specific
 *   regions. Toggle rates on or off without deleting them.
 *
 * **For Developers:**
 *   - Fetches tax rates via `GET /api/v1/stores/{store_id}/tax`.
 *   - Creates new rates via `POST /api/v1/stores/{store_id}/tax`.
 *   - Uses the `Switch` component for active/inactive toggling in the form.
 *   - Uses ``useStore()`` from store context for the store ID.
 *   - Wrapped in ``PageTransition`` for consistent entrance animation.
 *
 * **For QA Engineers:**
 *   - Verify that the tax rate list refreshes after creating a new rate.
 *   - Verify that the rate field accepts decimal percentages (e.g., 8.25).
 *   - Verify that empty state is shown when no tax rates exist.
 *   - Verify that error messages display when the API returns an error.
 *
 * **For Project Managers:**
 *   This page corresponds to Feature 16 (Tax) in the backlog.
 *   Tax rates are store-scoped and support region-based configuration.
 */

"use client";

import { FormEvent, useEffect, useState } from "react";
import { useAuth } from "@/contexts/auth-context";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import { PageTransition } from "@/components/motion-wrappers";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

/** Shape of a tax rate returned by the API. */
interface TaxRate {
  id: string;
  name: string;
  rate: number;
  country: string;
  state: string | null;
  is_active: boolean;
  created_at: string;
}

/**
 * TaxRatesPage renders the tax rate listing and creation form.
 *
 * Fetches tax rates from the API, displays them in a table, and
 * provides a dialog to create new rates. Uses the store context for
 * the store ID and PageTransition for entrance animation.
 *
 * @returns The rendered tax rates management page.
 */
export default function TaxRatesPage() {
  const { store } = useStore();
  const storeId = store!.id;
  const { user, loading: authLoading } = useAuth();
  const [taxRates, setTaxRates] = useState<TaxRate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* Create form state */
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formName, setFormName] = useState("");
  const [formRate, setFormRate] = useState("");
  const [formCountry, setFormCountry] = useState("");
  const [formState, setFormState] = useState("");
  const [formActive, setFormActive] = useState(true);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  /**
   * Fetch all tax rates for the current store.
   * Called on mount and after a successful creation.
   */
  async function fetchTaxRates() {
    setLoading(true);
    const result = await api.get<{ items: TaxRate[] }>(`/api/v1/stores/${storeId}/tax-rates`);
    if (result.error) {
      setError(result.error.message);
    } else {
      setTaxRates(result.data?.items ?? []);
    }
    setLoading(false);
  }

  useEffect(() => {
    if (authLoading || !user) return;
    fetchTaxRates();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storeId, user, authLoading]);

  /**
   * Handle the create-tax-rate form submission.
   * Sends a POST request and refreshes the list on success.
   *
   * @param e - The form submission event.
   */
  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    setCreateError(null);

    const result = await api.post<TaxRate>(`/api/v1/stores/${storeId}/tax-rates`, {
      name: formName,
      rate: parseFloat(formRate),
      country: formCountry,
      state: formState || null,
      is_active: formActive,
    });

    if (result.error) {
      setCreateError(result.error.message);
      setCreating(false);
      return;
    }

    /* Reset form and close dialog */
    setFormName("");
    setFormRate("");
    setFormCountry("");
    setFormState("");
    setFormActive(true);
    setDialogOpen(false);
    setCreating(false);
    fetchTaxRates();
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <p className="text-muted-foreground">Loading tax rates...</p>
      </div>
    );
  }

  return (
    <PageTransition>
      <main className="mx-auto max-w-4xl p-6 space-y-6">
        {/* Page heading and action */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold font-heading">Tax Rates</h1>
          <Button onClick={() => setDialogOpen(true)}>Add Tax Rate</Button>
        </div>

        {error && (
          <Card className="border-destructive/50">
            <CardContent className="pt-6">
              <p className="text-sm text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {taxRates.length === 0 ? (
          <div className="flex flex-col items-center gap-4 py-16 text-center">
            <div className="text-5xl opacity-20">%</div>
            <h2 className="text-xl font-semibold font-heading">No tax rates configured</h2>
            <p className="text-muted-foreground max-w-sm">
              Add your first tax rate to start collecting taxes on orders
              from specific regions.
            </p>
            <Button onClick={() => setDialogOpen(true)}>
              Add your first tax rate
            </Button>
          </div>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle className="font-heading">Tax Rates</CardTitle>
              <CardDescription>
                {taxRates.length} rate{taxRates.length !== 1 ? "s" : ""} configured
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Rate</TableHead>
                    <TableHead>Country</TableHead>
                    <TableHead>State</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {taxRates.map((rate) => (
                    <TableRow key={rate.id}>
                      <TableCell className="font-medium">{rate.name}</TableCell>
                      <TableCell>{rate.rate}%</TableCell>
                      <TableCell>{rate.country}</TableCell>
                      <TableCell>{rate.state || "--"}</TableCell>
                      <TableCell>
                        <Badge variant={rate.is_active ? "default" : "secondary"}>
                          {rate.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        {/* Create Tax Rate Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>New Tax Rate</DialogTitle>
              <DialogDescription>
                Configure a tax rate for a specific region.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              {createError && (
                <p className="text-sm text-destructive">{createError}</p>
              )}
              <div className="space-y-2">
                <Label htmlFor="tax-name">Name</Label>
                <Input
                  id="tax-name"
                  placeholder="e.g. State Sales Tax"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="tax-rate">Rate (%)</Label>
                <Input
                  id="tax-rate"
                  type="number"
                  step="any"
                  min="0"
                  max="100"
                  placeholder="8.25"
                  value={formRate}
                  onChange={(e) => setFormRate(e.target.value)}
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="tax-country">Country</Label>
                  <Input
                    id="tax-country"
                    placeholder="US"
                    value={formCountry}
                    onChange={(e) => setFormCountry(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tax-state">State / Province</Label>
                  <Input
                    id="tax-state"
                    placeholder="CA"
                    value={formState}
                    onChange={(e) => setFormState(e.target.value)}
                  />
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Switch
                  id="tax-active"
                  checked={formActive}
                  onCheckedChange={setFormActive}
                />
                <Label htmlFor="tax-active">Active</Label>
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
                  {creating ? "Creating..." : "Create Rate"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </main>
    </PageTransition>
  );
}
