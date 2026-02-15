/**
 * Create Product page.
 *
 * Provides a form for adding a new product to a store with title, price,
 * description, compare-at price, cost, status, SEO fields, and variants.
 *
 * **For End Users:**
 *   Fill in the product details and click "Create Product" to add it to
 *   your store. Products start as drafts by default -- set status to
 *   "Active" when ready to publish.
 *
 * **For QA Engineers:**
 *   - Title and price are required fields.
 *   - Price must be a valid non-negative number.
 *   - Variants can be added dynamically with name, SKU, price, and inventory.
 *   - On success, redirects to the product edit page.
 *   - The submit button is disabled while the request is in flight.
 *
 * **For Developers:**
 *   - Uses `useStore()` from the store context to obtain the store ID.
 *   - Wrapped in `<PageTransition>` for consistent page entrance animations.
 *   - The old breadcrumb header has been removed; navigation is handled
 *     by the shell sidebar.
 *
 * **For Project Managers:**
 *   Part of the product management CRUD flow. Creates a new product record
 *   under the current store.
 */

"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useStore } from "@/contexts/store-context";
import { api } from "@/lib/api";
import { PageTransition } from "@/components/motion-wrappers";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
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

/** Variant form data. */
interface VariantInput {
  name: string;
  sku: string;
  price: string;
  inventory_count: string;
}

/** Product response from the API. */
interface ProductResponse {
  id: string;
}

/**
 * Create product page component.
 *
 * Renders a multi-section form for creating a new product with details,
 * pricing, status, variants, and SEO fields.
 *
 * @returns The create product page wrapped in a PageTransition.
 */
export default function CreateProductPage() {
  const { store } = useStore();
  const storeId = store?.id ?? "";
  const router = useRouter();

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("");
  const [compareAtPrice, setCompareAtPrice] = useState("");
  const [cost, setCost] = useState("");
  const [status, setStatus] = useState("draft");
  const [seoTitle, setSeoTitle] = useState("");
  const [seoDescription, setSeoDescription] = useState("");
  const [variants, setVariants] = useState<VariantInput[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Add a new empty variant row to the variants list.
   */
  function addVariant() {
    setVariants([
      ...variants,
      { name: "", sku: "", price: "", inventory_count: "0" },
    ]);
  }

  /**
   * Remove a variant by its index in the list.
   * @param index - The zero-based index of the variant to remove.
   */
  function removeVariant(index: number) {
    setVariants(variants.filter((_, i) => i !== index));
  }

  /**
   * Update a single field of a variant by index.
   * @param index - The zero-based index of the variant to update.
   * @param field - The field key to update.
   * @param value - The new value for the field.
   */
  function updateVariant(index: number, field: keyof VariantInput, value: string) {
    const updated = [...variants];
    updated[index] = { ...updated[index], [field]: value };
    setVariants(updated);
  }

  /**
   * Handle form submission -- create the product via API.
   *
   * Constructs the request body from form state and sends a POST request.
   * On success, redirects to the product edit page.
   * @param e - The form submission event.
   */
  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    const body: Record<string, unknown> = {
      title,
      price: parseFloat(price),
      description: description || null,
      status,
      seo_title: seoTitle || null,
      seo_description: seoDescription || null,
    };

    if (compareAtPrice) body.compare_at_price = parseFloat(compareAtPrice);
    if (cost) body.cost = parseFloat(cost);

    if (variants.length > 0) {
      body.variants = variants
        .filter((v) => v.name.trim())
        .map((v) => ({
          name: v.name,
          sku: v.sku || null,
          price: v.price ? parseFloat(v.price) : null,
          inventory_count: parseInt(v.inventory_count) || 0,
        }));
    }

    const result = await api.post<ProductResponse>(
      `/api/v1/stores/${storeId}/products`,
      body
    );

    if (result.error) {
      setError(result.error.message);
      setSubmitting(false);
      return;
    }

    router.push(`/stores/${storeId}/products/${result.data!.id}`);
  }

  return (
    <PageTransition>
      <main className="mx-auto max-w-4xl p-6 space-y-6">
        {/* Page heading */}
        <h1 className="text-2xl font-heading font-bold">New Product</h1>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Info */}
          <Card>
            <CardHeader>
              <CardTitle>Product Details</CardTitle>
              <CardDescription>
                Add a title, description, and pricing for your product.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {error && (
                <p className="text-sm text-destructive text-center">{error}</p>
              )}
              <div className="space-y-2">
                <Label htmlFor="title">Title</Label>
                <Input
                  id="title"
                  placeholder="Product title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                  maxLength={500}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="Describe your product..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={4}
                />
              </div>
            </CardContent>
          </Card>

          {/* Pricing */}
          <Card>
            <CardHeader>
              <CardTitle>Pricing</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="price">Price</Label>
                  <Input
                    id="price"
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="0.00"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="compareAtPrice">Compare-at Price</Label>
                  <Input
                    id="compareAtPrice"
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="0.00"
                    value={compareAtPrice}
                    onChange={(e) => setCompareAtPrice(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="cost">Cost</Label>
                  <Input
                    id="cost"
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="0.00"
                    value={cost}
                    onChange={(e) => setCost(e.target.value)}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Status */}
          <Card>
            <CardHeader>
              <CardTitle>Status</CardTitle>
            </CardHeader>
            <CardContent>
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="draft">Draft</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                </SelectContent>
              </Select>
            </CardContent>
          </Card>

          {/* Variants */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Variants</CardTitle>
                <Button type="button" variant="outline" size="sm" onClick={addVariant}>
                  Add Variant
                </Button>
              </div>
              <CardDescription>
                Add size, color, or other product options.
              </CardDescription>
            </CardHeader>
            {variants.length > 0 && (
              <CardContent className="space-y-4">
                {variants.map((variant, index) => (
                  <div
                    key={index}
                    className="grid grid-cols-5 gap-2 items-end border-b pb-4 last:border-0"
                  >
                    <div className="space-y-1">
                      <Label className="text-xs">Name</Label>
                      <Input
                        placeholder="e.g. Large"
                        value={variant.name}
                        onChange={(e) =>
                          updateVariant(index, "name", e.target.value)
                        }
                        required
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">SKU</Label>
                      <Input
                        placeholder="SKU"
                        value={variant.sku}
                        onChange={(e) =>
                          updateVariant(index, "sku", e.target.value)
                        }
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Price</Label>
                      <Input
                        type="number"
                        step="0.01"
                        min="0"
                        placeholder="Override"
                        value={variant.price}
                        onChange={(e) =>
                          updateVariant(index, "price", e.target.value)
                        }
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Stock</Label>
                      <Input
                        type="number"
                        min="0"
                        value={variant.inventory_count}
                        onChange={(e) =>
                          updateVariant(index, "inventory_count", e.target.value)
                        }
                      />
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeVariant(index)}
                      className="text-destructive"
                    >
                      Remove
                    </Button>
                  </div>
                ))}
              </CardContent>
            )}
          </Card>

          {/* SEO */}
          <Card>
            <CardHeader>
              <CardTitle>SEO</CardTitle>
              <CardDescription>
                Customize how this product appears in search engines.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="seoTitle">SEO Title</Label>
                <Input
                  id="seoTitle"
                  placeholder="Custom search engine title"
                  value={seoTitle}
                  onChange={(e) => setSeoTitle(e.target.value)}
                  maxLength={255}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="seoDescription">SEO Description</Label>
                <Textarea
                  id="seoDescription"
                  placeholder="Custom search engine description"
                  value={seoDescription}
                  onChange={(e) => setSeoDescription(e.target.value)}
                  rows={2}
                />
              </div>
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex justify-end gap-2">
            <Link href={`/stores/${storeId}/products`}>
              <Button type="button" variant="outline">
                Cancel
              </Button>
            </Link>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Creating..." : "Create Product"}
            </Button>
          </div>
        </form>
      </main>
    </PageTransition>
  );
}
