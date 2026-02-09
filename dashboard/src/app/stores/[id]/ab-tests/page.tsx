/**
 * A/B Tests management page.
 *
 * Lists all A/B tests for a store with their names, statuses, variants,
 * and conversion data. Provides a dialog to create new split tests.
 *
 * **For End Users:**
 *   Run experiments on your storefront to discover what converts best.
 *   Create A/B tests with multiple variants, track impressions and
 *   conversions, and pick winners based on data.
 *
 * **For Developers:**
 *   - Fetches tests via `GET /api/v1/stores/{store_id}/ab-tests`.
 *   - Creates new tests via `POST /api/v1/stores/{store_id}/ab-tests`.
 *   - Variants are submitted as a JSON array of `{ name, weight }` objects.
 *   - Uses `useStore()` context for store ID (provided by the layout).
 *   - Wrapped in `PageTransition` for consistent page-level animations.
 *
 * **For QA Engineers:**
 *   - Verify the test list refreshes after creating a new test.
 *   - Verify that at least two variants are required.
 *   - Verify that variant weights are between 0 and 100.
 *   - Verify that test statuses (draft, running, completed) display correctly.
 *   - Verify empty state when no tests exist.
 *
 * **For Project Managers:**
 *   This page corresponds to Feature 29 (A/B Testing) in the backlog.
 *   A/B testing enables data-driven optimization of the storefront.
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
import { Textarea } from "@/components/ui/textarea";
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

/** Shape of a variant within an A/B test. */
interface Variant {
  name: string;
  weight: number;
  impressions: number;
  conversions: number;
}

/** Shape of an A/B test returned by the API. */
interface ABTest {
  id: string;
  name: string;
  description: string | null;
  status: "draft" | "running" | "paused" | "completed";
  test_type: "page" | "price" | "layout" | "copy";
  variants: Variant[];
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
}

/** Temporary state for a variant being added in the creation form. */
interface VariantInput {
  name: string;
  weight: string;
}

/**
 * ABTestsPage renders the A/B test listing and creation dialog.
 *
 * Retrieves the store ID from the StoreContext (provided by the parent layout)
 * and fetches all A/B tests for that store. Provides a dialog form to create
 * new experiments with multiple variants and weight assignments.
 *
 * @returns The rendered A/B tests management page.
 */
export default function ABTestsPage() {
  const { store: contextStore } = useStore();
  const id = contextStore!.id;
  const { user, loading: authLoading } = useAuth();
  const [tests, setTests] = useState<ABTest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* Create form state */
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formName, setFormName] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formType, setFormType] = useState<ABTest["test_type"]>("page");
  const [formVariants, setFormVariants] = useState<VariantInput[]>([
    { name: "Control", weight: "50" },
    { name: "Variant B", weight: "50" },
  ]);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  /**
   * Fetch all A/B tests for this store.
   */
  async function fetchTests() {
    setLoading(true);
    const result = await api.get<{ items: ABTest[]; total: number }>(
      `/api/v1/stores/${id}/ab-tests`
    );
    if (result.error) {
      setError(result.error.message);
    } else {
      setTests(result.data?.items ?? []);
    }
    setLoading(false);
  }

  useEffect(() => {
    if (authLoading || !user) return;
    fetchTests();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, user, authLoading]);

  /**
   * Add a blank variant row to the form.
   */
  function addVariant() {
    setFormVariants((prev) => [...prev, { name: "", weight: "0" }]);
  }

  /**
   * Remove a variant row from the form by index.
   *
   * @param index - The zero-based index to remove.
   */
  function removeVariant(index: number) {
    if (formVariants.length <= 2) return;
    setFormVariants((prev) => prev.filter((_, i) => i !== index));
  }

  /**
   * Update a variant field in the form.
   *
   * @param index - The variant index to update.
   * @param field - The field name ("name" or "weight").
   * @param value - The new value.
   */
  function updateVariant(
    index: number,
    field: keyof VariantInput,
    value: string
  ) {
    setFormVariants((prev) =>
      prev.map((v, i) => (i === index ? { ...v, [field]: value } : v))
    );
  }

  /**
   * Handle the create-test form submission.
   *
   * @param e - The form submission event.
   */
  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    setCreateError(null);

    const variants = formVariants.map((v) => ({
      name: v.name,
      weight: parseInt(v.weight, 10),
    }));

    if (variants.some((v) => !v.name)) {
      setCreateError("All variants must have a name.");
      setCreating(false);
      return;
    }

    const result = await api.post<ABTest>(
      `/api/v1/stores/${id}/ab-tests`,
      {
        name: formName,
        description: formDescription || null,
        metric: "conversion_rate",
        variants,
      }
    );

    if (result.error) {
      setCreateError(result.error.message);
      setCreating(false);
      return;
    }

    setFormName("");
    setFormDescription("");
    setFormType("page");
    setFormVariants([
      { name: "Control", weight: "50" },
      { name: "Variant B", weight: "50" },
    ]);
    setDialogOpen(false);
    setCreating(false);
    fetchTests();
  }

  /**
   * Map test status to a Badge variant.
   *
   * @param status - The A/B test status.
   * @returns The appropriate Badge variant.
   */
  function statusVariant(
    status: ABTest["status"]
  ): "default" | "secondary" | "outline" | "destructive" {
    switch (status) {
      case "running":
        return "default";
      case "draft":
        return "secondary";
      case "completed":
        return "outline";
      case "paused":
        return "destructive";
      default:
        return "outline";
    }
  }

  /**
   * Calculate the total conversion rate across all variants.
   *
   * @param variants - Array of variant objects with impressions and conversions.
   * @returns The overall conversion rate as a percentage string.
   */
  function totalConversionRate(variants: Variant[]): string {
    const totalImpressions = variants.reduce((s, v) => s + v.impressions, 0);
    const totalConversions = variants.reduce((s, v) => s + v.conversions, 0);
    if (totalImpressions === 0) return "0.0%";
    return ((totalConversions / totalImpressions) * 100).toFixed(1) + "%";
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <p className="text-muted-foreground">Loading A/B tests...</p>
      </div>
    );
  }

  return (
    <PageTransition>
      <main className="mx-auto max-w-4xl p-6 space-y-6">
        {/* Page heading and create button */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold font-heading">A/B Tests</h1>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button>Create Test</Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-lg">
              <DialogHeader>
                <DialogTitle>New A/B Test</DialogTitle>
                <DialogDescription>
                  Set up an experiment with multiple variants. Traffic will be
                  split according to the weights you assign.
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreate} className="space-y-4">
                {createError && (
                  <p className="text-sm text-destructive">{createError}</p>
                )}
                <div className="space-y-2">
                  <Label htmlFor="ab-name">Test Name</Label>
                  <Input
                    id="ab-name"
                    placeholder="e.g. Homepage Hero Banner"
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="ab-desc">Description</Label>
                  <Textarea
                    id="ab-desc"
                    placeholder="What are you testing?"
                    value={formDescription}
                    onChange={(e) => setFormDescription(e.target.value)}
                    rows={2}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="ab-type">Test Type</Label>
                  <Select
                    value={formType}
                    onValueChange={(v) =>
                      setFormType(v as ABTest["test_type"])
                    }
                  >
                    <SelectTrigger id="ab-type">
                      <SelectValue placeholder="Select type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="page">Page</SelectItem>
                      <SelectItem value="price">Price</SelectItem>
                      <SelectItem value="layout">Layout</SelectItem>
                      <SelectItem value="copy">Copy</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Variants */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label>Variants</Label>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={addVariant}
                    >
                      + Add Variant
                    </Button>
                  </div>
                  {formVariants.map((variant, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <Input
                        placeholder="Variant name"
                        value={variant.name}
                        onChange={(e) =>
                          updateVariant(idx, "name", e.target.value)
                        }
                        required
                        className="flex-1"
                      />
                      <Input
                        type="number"
                        min="0"
                        max="100"
                        placeholder="Weight %"
                        value={variant.weight}
                        onChange={(e) =>
                          updateVariant(idx, "weight", e.target.value)
                        }
                        className="w-24"
                      />
                      {formVariants.length > 2 && (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => removeVariant(idx)}
                        >
                          X
                        </Button>
                      )}
                    </div>
                  ))}
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
                    {creating ? "Creating..." : "Create Test"}
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {error && (
          <Card className="border-destructive/50">
            <CardContent className="pt-6">
              <p className="text-sm text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {tests.length === 0 ? (
          <div className="flex flex-col items-center gap-4 py-16 text-center">
            <div className="text-5xl opacity-20">A|B</div>
            <h2 className="text-xl font-semibold font-heading">No A/B tests yet</h2>
            <p className="text-muted-foreground max-w-sm">
              Create your first experiment to start testing what converts
              best on your storefront.
            </p>
            <Button onClick={() => setDialogOpen(true)}>
              Create your first test
            </Button>
          </div>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Experiments</CardTitle>
              <CardDescription>
                {tests.length} test{tests.length !== 1 ? "s" : ""}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Variants</TableHead>
                    <TableHead>Conversion Rate</TableHead>
                    <TableHead>Created</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tests.map((test) => (
                    <TableRow key={test.id}>
                      <TableCell>
                        <div>
                          <span className="font-medium">{test.name}</span>
                          {test.description && (
                            <p className="text-xs text-muted-foreground mt-0.5 max-w-xs truncate">
                              {test.description}
                            </p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{test.test_type}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusVariant(test.status)}>
                          {test.status}
                        </Badge>
                      </TableCell>
                      <TableCell>{test.variants.length}</TableCell>
                      <TableCell className="font-medium">
                        {totalConversionRate(test.variants)}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {new Date(test.created_at).toLocaleDateString()}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </main>
    </PageTransition>
  );
}
