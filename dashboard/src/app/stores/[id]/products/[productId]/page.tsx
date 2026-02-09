/**
 * Product edit/settings page.
 *
 * Displays the details of a single product and provides forms to update
 * its fields, manage variants, upload images, or soft-delete it.
 *
 * **For End Users:**
 *   Edit your product's title, pricing, description, variants, and SEO
 *   settings. Upload images to showcase your product. Delete products
 *   you no longer need.
 *
 * **For QA Engineers:**
 *   - The page loads the product by product ID from the URL parameter.
 *   - The store ID comes from the StoreProvider context.
 *   - If the product is not found (404), a "Product not found" message is shown.
 *   - Image upload uses multipart form data via the upload endpoint.
 *   - Delete shows a confirmation dialog before soft-deleting.
 *   - After deletion, the user is redirected to the products list.
 *   - Updating the title triggers slug regeneration on the backend.
 *
 * **For Developers:**
 *   - Uses `useStore()` from the store context to obtain the store ID.
 *   - Still reads `productId` from the URL params via `use(params)`.
 *   - Wrapped in `<PageTransition>` for consistent page entrance animations.
 *   - The old breadcrumb header has been removed; navigation is handled
 *     by the shell sidebar.
 *
 * **For Project Managers:**
 *   Core product editing flow. Allows store owners to modify any product
 *   field, manage variants, upload images, and delete products.
 */

"use client";

import { FormEvent, useEffect, useState, use, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
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

/** Variant data from the API. */
interface Variant {
  id: string;
  name: string;
  sku: string | null;
  price: string | null;
  inventory_count: number;
}

/** Variant form input. */
interface VariantInput {
  name: string;
  sku: string;
  price: string;
  inventory_count: string;
}

/** Full product data from the API. */
interface Product {
  id: string;
  store_id: string;
  title: string;
  slug: string;
  description: string | null;
  price: string;
  compare_at_price: string | null;
  cost: string | null;
  images: string[] | null;
  status: "draft" | "active" | "archived";
  seo_title: string | null;
  seo_description: string | null;
  created_at: string;
  updated_at: string;
  variants: Variant[];
}

/**
 * Product edit page component.
 *
 * Renders the full product edit form including details, images, pricing,
 * status, variants, SEO, and a danger zone for deletion.
 *
 * @param props - Page props containing the productId parameter.
 * @returns The product edit page wrapped in a PageTransition.
 */
export default function ProductEditPage({
  params,
}: {
  params: Promise<{ id: string; productId: string }>;
}) {
  const { productId } = use(params);
  const { store } = useStore();
  const storeId = store?.id ?? "";
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  // Edit form state
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("");
  const [compareAtPrice, setCompareAtPrice] = useState("");
  const [cost, setCost] = useState("");
  const [status, setStatus] = useState("draft");
  const [seoTitle, setSeoTitle] = useState("");
  const [seoDescription, setSeoDescription] = useState("");
  const [images, setImages] = useState<string[]>([]);
  const [variants, setVariants] = useState<VariantInput[]>([]);

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [uploading, setUploading] = useState(false);

  // Delete state
  const [deleting, setDeleting] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  useEffect(() => {
    if (authLoading || !user || !storeId) return;

    /**
     * Fetch the product record from the API and populate form state.
     */
    async function fetchProduct() {
      const result = await api.get<Product>(
        `/api/v1/stores/${storeId}/products/${productId}`
      );
      if (result.error) {
        setNotFound(true);
        setLoading(false);
        return;
      }
      const p = result.data!;
      setProduct(p);
      setTitle(p.title);
      setDescription(p.description || "");
      setPrice(p.price);
      setCompareAtPrice(p.compare_at_price || "");
      setCost(p.cost || "");
      setStatus(p.status);
      setSeoTitle(p.seo_title || "");
      setSeoDescription(p.seo_description || "");
      setImages(p.images || []);
      setVariants(
        p.variants.map((v) => ({
          name: v.name,
          sku: v.sku || "",
          price: v.price || "",
          inventory_count: String(v.inventory_count),
        }))
      );
      setLoading(false);
    }

    fetchProduct();
  }, [storeId, productId, user, authLoading]);

  /**
   * Handle image upload via multipart form data.
   * @param e - The file input change event.
   */
  async function handleImageUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    const result = await api.upload<{ url: string }>(
      `/api/v1/stores/${storeId}/products/upload`,
      file
    );

    if (result.data) {
      setImages([...images, result.data.url]);
    }
    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  /**
   * Remove an image by its index in the images array.
   * @param index - The zero-based index of the image to remove.
   */
  function removeImage(index: number) {
    setImages(images.filter((_, i) => i !== index));
  }

  /**
   * Add a new empty variant row.
   */
  function addVariant() {
    setVariants([
      ...variants,
      { name: "", sku: "", price: "", inventory_count: "0" },
    ]);
  }

  /**
   * Remove a variant by its index.
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
   * Handle the update form submission.
   *
   * Sends a PATCH request with the updated product data.
   * @param e - The form submission event.
   */
  async function handleUpdate(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);

    const body: Record<string, unknown> = {
      title,
      description: description || null,
      price: parseFloat(price),
      status,
      images,
      seo_title: seoTitle || null,
      seo_description: seoDescription || null,
    };

    if (compareAtPrice) body.compare_at_price = parseFloat(compareAtPrice);
    if (cost) body.cost = parseFloat(cost);

    body.variants = variants
      .filter((v) => v.name.trim())
      .map((v) => ({
        name: v.name,
        sku: v.sku || null,
        price: v.price ? parseFloat(v.price) : null,
        inventory_count: parseInt(v.inventory_count) || 0,
      }));

    const result = await api.patch<Product>(
      `/api/v1/stores/${storeId}/products/${productId}`,
      body
    );

    if (result.error) {
      setSaveError(result.error.message);
      setSaving(false);
      return;
    }

    setProduct(result.data!);
    setSaveSuccess(true);
    setSaving(false);
    setTimeout(() => setSaveSuccess(false), 3000);
  }

  /**
   * Handle the delete confirmation.
   *
   * Sends a DELETE request and redirects to the products list.
   */
  async function handleDelete() {
    setDeleting(true);
    await api.delete(`/api/v1/stores/${storeId}/products/${productId}`);
    setDeleteDialogOpen(false);
    router.push(`/stores/${storeId}/products`);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-muted-foreground">Loading product...</p>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-20">
        <h2 className="text-xl font-semibold">Product not found</h2>
        <Link href={`/stores/${storeId}/products`}>
          <Button variant="outline">Back to products</Button>
        </Link>
      </div>
    );
  }

  return (
    <PageTransition>
      <main className="mx-auto max-w-4xl p-6 space-y-6">
        {/* Page heading */}
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-heading font-bold">{product?.title}</h1>
          {product && (
            <Badge
              variant={
                product.status === "active"
                  ? "default"
                  : product.status === "draft"
                    ? "secondary"
                    : "outline"
              }
            >
              {product.status}
            </Badge>
          )}
        </div>

        <form onSubmit={handleUpdate} className="space-y-6">
          {/* Basic Info */}
          <Card>
            <CardHeader>
              <CardTitle>Product Details</CardTitle>
              <CardDescription>
                Slug:{" "}
                <code className="rounded bg-muted px-1.5 py-0.5 text-xs">
                  {product?.slug}
                </code>
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {saveError && (
                <p className="text-sm text-destructive">{saveError}</p>
              )}
              {saveSuccess && (
                <p className="text-sm text-green-600">
                  Product updated successfully.
                </p>
              )}
              <div className="space-y-2">
                <Label htmlFor="title">Title</Label>
                <Input
                  id="title"
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
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={4}
                />
              </div>
            </CardContent>
          </Card>

          {/* Images */}
          <Card>
            <CardHeader>
              <CardTitle>Images</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-4 gap-3">
                {images.map((url, index) => (
                  <div key={index} className="relative group">
                    <div className="aspect-square rounded-lg border bg-muted overflow-hidden">
                      <img
                        src={url}
                        alt={`Product image ${index + 1}`}
                        className="h-full w-full object-cover"
                      />
                    </div>
                    <button
                      type="button"
                      onClick={() => removeImage(index)}
                      className="absolute -top-2 -right-2 bg-destructive text-white rounded-full w-5 h-5 text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      x
                    </button>
                  </div>
                ))}
                <label className="aspect-square rounded-lg border-2 border-dashed border-muted-foreground/25 flex items-center justify-center cursor-pointer hover:border-muted-foreground/50 transition-colors">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp,image/gif"
                    onChange={handleImageUpload}
                    className="hidden"
                  />
                  <span className="text-2xl text-muted-foreground/50">
                    {uploading ? "..." : "+"}
                  </span>
                </label>
              </div>
            </CardContent>
          </Card>

          {/* Pricing */}
          <Card>
            <CardHeader>
              <CardTitle>Pricing</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="price">Price</Label>
                  <Input
                    id="price"
                    type="number"
                    step="0.01"
                    min="0"
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
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={addVariant}
                >
                  Add Variant
                </Button>
              </div>
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
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="seoTitle">SEO Title</Label>
                <Input
                  id="seoTitle"
                  value={seoTitle}
                  onChange={(e) => setSeoTitle(e.target.value)}
                  maxLength={255}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="seoDescription">SEO Description</Label>
                <Textarea
                  id="seoDescription"
                  value={seoDescription}
                  onChange={(e) => setSeoDescription(e.target.value)}
                  rows={2}
                />
              </div>
            </CardContent>
          </Card>

          {/* Save */}
          <div className="flex justify-end">
            <Button type="submit" disabled={saving}>
              {saving ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </form>

        {/* Danger Zone */}
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="text-destructive">Danger Zone</CardTitle>
            <CardDescription>
              Deleting a product removes it from your store permanently.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="destructive">Delete Product</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>
                    Delete &quot;{product?.title}&quot;?
                  </DialogTitle>
                  <DialogDescription>
                    This action cannot be undone. The product will be archived
                    and removed from your store.
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
