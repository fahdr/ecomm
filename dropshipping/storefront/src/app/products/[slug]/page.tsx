/**
 * Product detail page for the storefront.
 *
 * Displays a single product with images, title, description, price,
 * variants, and SEO metadata. Fetched server-side from the public API.
 *
 * **For Developers:**
 *   This is a server component. The product slug comes from the URL
 *   parameter. Dynamic SEO metadata is generated via ``generateMetadata``.
 *
 * **For QA Engineers:**
 *   - Only active products are shown; draft/archived return 404.
 *   - Compare-at price shows with a strikethrough if present.
 *   - Variants are listed with name, price override, and stock.
 *   - ``<title>`` and ``<meta description>`` are set from product data.
 *   - Product images display in a gallery layout.
 *
 * **For End Users:**
 *   View product details including images, description, price, and
 *   available variants before purchasing.
 */

import { headers } from "next/headers";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import Link from "next/link";
import { fetchStore } from "@/lib/store";
import { api } from "@/lib/api";
import type { Product } from "@/lib/types";
import { AddToCart } from "@/components/add-to-cart";
import { ProductReviews } from "@/components/product-reviews";
import { ProductUpsells } from "@/components/product-upsells";
import { ProductViewTracker } from "@/components/product-view-tracker";

/**
 * Generate dynamic metadata for the product detail page.
 *
 * @param props - Page props containing the product slug parameter.
 * @returns Metadata object with product title and description.
 */
export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const headersList = await headers();
  const storeSlug = headersList.get("x-store-slug");

  if (!storeSlug) {
    return { title: "Product Not Found" };
  }

  const { slug: productSlug } = await params;
  const { data: product } = await api.get<Product>(
    `/api/v1/public/stores/${encodeURIComponent(storeSlug)}/products/${encodeURIComponent(productSlug)}`
  );

  if (!product) {
    return { title: "Product Not Found" };
  }

  return {
    title: product.seo_title || product.title,
    description:
      product.seo_description ||
      product.description?.slice(0, 160) ||
      `Buy ${product.title}`,
    openGraph: {
      title: product.seo_title || product.title,
      description:
        product.seo_description ||
        product.description?.slice(0, 160) ||
        `Buy ${product.title}`,
      images: product.images?.[0] ? [product.images[0]] : [],
    },
  };
}

/**
 * Product detail page server component.
 *
 * @param props - Page props containing the product slug parameter.
 * @returns The product detail layout with images, info, and variants.
 */
export default async function ProductDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const headersList = await headers();
  const storeSlug = headersList.get("x-store-slug");

  if (!storeSlug) {
    notFound();
  }

  const store = await fetchStore(storeSlug);
  if (!store) {
    notFound();
  }

  const { slug: productSlug } = await params;
  const { data: product } = await api.get<Product>(
    `/api/v1/public/stores/${encodeURIComponent(storeSlug)}/products/${encodeURIComponent(productSlug)}`
  );

  if (!product) {
    notFound();
  }

  return (
    <div className="py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Breadcrumb */}
        <nav className="mb-8 text-sm text-theme-muted">
          <Link href="/" className="hover:text-theme-primary transition-colors">
            Home
          </Link>
          <span className="mx-2">/</span>
          <Link
            href="/products"
            className="hover:text-theme-primary transition-colors"
          >
            Products
          </Link>
          <span className="mx-2">/</span>
          <span>
            {product.title}
          </span>
        </nav>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
          {/* Image Gallery */}
          <div className="space-y-4">
            {product.images && product.images.length > 0 ? (
              <>
                {/* Main image */}
                <div className="aspect-square rounded-lg overflow-hidden bg-theme-surface">
                  <img
                    src={product.images[0]}
                    alt={product.title}
                    className="h-full w-full object-cover"
                  />
                </div>
                {/* Thumbnails */}
                {product.images.length > 1 && (
                  <div className="grid grid-cols-4 gap-3">
                    {product.images.slice(1).map((img, i) => (
                      <div
                        key={i}
                        className="aspect-square rounded-lg overflow-hidden bg-theme-surface"
                      >
                        <img
                          src={img}
                          alt={`${product.title} image ${i + 2}`}
                          className="h-full w-full object-cover"
                        />
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className="aspect-square rounded-lg bg-theme-surface flex items-center justify-center">
                <div className="w-24 h-24 rounded-full bg-theme-surface/50" />
              </div>
            )}
          </div>

          {/* Product Info */}
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              {product.title}
            </h1>

            {/* Price */}
            <div className="mt-4 flex items-center gap-3">
              <span className="text-3xl font-bold">
                ${Number(product.price).toFixed(2)}
              </span>
              {product.compare_at_price && (
                <span className="text-xl text-theme-muted line-through">
                  ${Number(product.compare_at_price).toFixed(2)}
                </span>
              )}
            </div>

            {/* Description */}
            {product.description && (
              <div className="mt-8">
                <h3 className="text-sm font-medium text-theme-muted uppercase tracking-wide mb-3">
                  Description
                </h3>
                <div className="text-theme-muted leading-relaxed">
                  <p>{product.description}</p>
                </div>
              </div>
            )}

            {/* Add to Cart */}
            <AddToCart
              productId={product.id}
              title={product.title}
              slug={product.slug}
              price={product.price}
              image={product.images?.[0] || null}
              variants={product.variants}
            />
          </div>
        </div>

        {/* Reviews Section */}
        <ProductReviews storeSlug={storeSlug} productSlug={productSlug} />

        {/* Upsells / Cross-Sells Section */}
        <ProductUpsells storeSlug={storeSlug} productSlug={productSlug} />
      </div>

      {/* Recently Viewed Products */}
      <ProductViewTracker slug={productSlug} />
    </div>
  );
}
