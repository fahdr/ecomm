/**
 * Hero Banner block -- a full-width introductory section for the storefront
 * homepage with support for gradient/solid/image backgrounds and a dynamic
 * product showcase mode.
 *
 * **For Developers:**
 *   This is a **client component** (needs state for product showcase mode).
 *   Background types:
 *     - ``"gradient"`` (default): linear-gradient from primary to accent.
 *     - ``"solid"``: uses primary color as a flat background.
 *     - ``"image"``: background image from ``config.bg_image`` with overlay.
 *     - ``"product_showcase"``: fetches featured products and displays them
 *       with animated entrance alongside the hero text.
 *   Additional config options:
 *     - ``text_position`` ("left" | "center" | "right") -- Text alignment.
 *     - ``height`` ("sm" | "md" | "lg" | "full") -- Viewport height.
 *     - ``overlay_style`` ("gradient" | "blur" | "dark" | "none") -- Overlay.
 *     - ``featured_product_ids`` (string[]) -- Product IDs for showcase mode.
 *
 * **For QA Engineers:**
 *   - Missing ``title`` defaults to "Welcome to our store".
 *   - Missing ``cta_text`` defaults to "Shop Now".
 *   - ``bg_type`` defaults to "gradient" when unspecified.
 *   - Product showcase fetches 1-3 products via public API.
 *   - Height options map: sm=py-16, md=py-24, lg=py-32/40, full=min-h-screen.
 *
 * **For Project Managers:**
 *   The hero banner is the first thing customers see. Store owners can now
 *   showcase their best products directly in the hero, with configurable
 *   text positioning and height to match their brand aesthetic.
 *
 * **For End Users:**
 *   The large banner at the top of the store homepage showcasing featured
 *   products and the store's branding.
 *
 * @module blocks/hero-banner
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useStore } from "@/contexts/store-context";
import type { Product } from "@/lib/types";

/** Props accepted by the {@link HeroBanner} component. */
interface HeroBannerProps {
  config: Record<string, unknown>;
}

/**
 * Map height config to Tailwind padding classes.
 * @param height - Height option string.
 * @returns Tailwind padding class string.
 */
function heightClasses(height: string): string {
  switch (height) {
    case "sm": return "py-16 sm:py-20";
    case "md": return "py-20 sm:py-28";
    case "full": return "min-h-[80vh] flex items-center";
    case "lg":
    default: return "py-24 sm:py-32 lg:py-40";
  }
}

/**
 * Map text position to Tailwind alignment classes.
 * @param pos - Text position option.
 * @returns Tailwind text alignment classes.
 */
function textAlignClasses(pos: string): string {
  switch (pos) {
    case "left": return "text-left items-start";
    case "right": return "text-right items-end";
    case "center":
    default: return "text-center items-center";
  }
}

/**
 * Map overlay style to CSS classes.
 * @param style - Overlay style option.
 * @returns CSS class string for the overlay div.
 */
function overlayClasses(style: string): string {
  switch (style) {
    case "blur": return "absolute inset-0 bg-black/30 backdrop-blur-sm";
    case "dark": return "absolute inset-0 bg-black/60";
    case "none": return "hidden";
    case "gradient":
    default: return "absolute inset-0 bg-gradient-to-r from-black/60 via-black/30 to-transparent";
  }
}

/**
 * Render a full-width hero banner with heading, subtitle, CTA, and optional
 * product showcase.
 *
 * @param props - Component props.
 * @param props.config - Block configuration from the store theme.
 * @returns A ``<section>`` element with the hero content.
 */
export function HeroBanner({ config }: HeroBannerProps) {
  const store = useStore();
  const title = (config.title as string) || "Welcome to our store";
  const subtitle = (config.subtitle as string) || "";
  const ctaText = (config.cta_text as string) || "Shop Now";
  const ctaLink = (config.cta_link as string) || "/products";
  const bgType = (config.bg_type as string) || "gradient";
  const bgImage = (config.bg_image as string) || "";
  const textPosition = (config.text_position as string) || "center";
  const height = (config.height as string) || "lg";
  const overlayStyle = (config.overlay_style as string) || "gradient";
  const featuredProductIds = Array.isArray(config.featured_product_ids)
    ? (config.featured_product_ids as string[])
    : [];

  const isShowcase = bgType === "product_showcase";
  const [products, setProducts] = useState<Product[]>([]);

  /** Fetch featured products for showcase mode. */
  useEffect(() => {
    if (!isShowcase || !store || featuredProductIds.length === 0) return;
    let cancelled = false;

    async function fetchProducts() {
      // Fetch all products and filter by IDs (public API doesn't support
      // filtering by IDs directly, so we fetch a batch and filter client-side)
      const { data } = await api.get<{ items: Product[] }>(
        `/api/v1/public/stores/${encodeURIComponent(store!.slug)}/products?per_page=50`
      );
      if (!cancelled && data) {
        const matched = data.items.filter((p) =>
          featuredProductIds.includes(p.id)
        );
        // Maintain the order of featuredProductIds
        const ordered = featuredProductIds
          .map((id) => matched.find((p) => p.id === id))
          .filter((p): p is Product => !!p);
        setProducts(ordered.length > 0 ? ordered : data.items.slice(0, 3));
      }
    }

    fetchProducts();
    return () => { cancelled = true; };
  }, [isShowcase, store, featuredProductIds.join(",")]);

  /** Build background inline styles. */
  const bgStyles: React.CSSProperties = {};
  let needsOverlay = false;

  if (bgType === "image" && bgImage) {
    bgStyles.backgroundImage = `url(${bgImage})`;
    bgStyles.backgroundSize = "cover";
    bgStyles.backgroundPosition = "center";
    needsOverlay = true;
  } else if (bgType === "solid") {
    bgStyles.backgroundColor = "var(--theme-primary)";
    bgStyles.color = "var(--theme-primary-text)";
  } else if (isShowcase) {
    bgStyles.background =
      "linear-gradient(135deg, var(--theme-primary) 0%, var(--theme-accent) 100%)";
    bgStyles.color = "var(--theme-primary-text)";
  } else {
    bgStyles.background =
      "linear-gradient(135deg, var(--theme-primary) 0%, var(--theme-accent) 100%)";
    bgStyles.color = "var(--theme-primary-text)";
  }

  return (
    <section
      className="relative w-full overflow-hidden"
      style={bgStyles}
    >
      {/* Overlay for image backgrounds */}
      {needsOverlay && (
        <div className={overlayClasses(overlayStyle)} aria-hidden="true" />
      )}

      <div
        className={`relative mx-auto max-w-7xl px-6 ${heightClasses(height)} ${
          isShowcase && products.length > 0
            ? "grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12"
            : ""
        }`}
      >
        {/* Text content */}
        <div className={`flex flex-col justify-center ${textAlignClasses(textPosition)} ${
          isShowcase && products.length > 0 ? "py-12 lg:py-0" : ""
        }`}>
          <h1 className="font-heading text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-tight">
            {title}
          </h1>

          {subtitle && (
            <p className={`mt-6 max-w-2xl text-lg sm:text-xl opacity-90 leading-relaxed ${
              textPosition === "center" ? "mx-auto" : ""
            }`}>
              {subtitle}
            </p>
          )}

          <div className="mt-10">
            <Link
              href={ctaLink}
              className="inline-block btn-primary px-8 py-3.5 text-base font-semibold shadow-lg hover:shadow-xl transition-shadow"
            >
              {ctaText}
            </Link>
          </div>
        </div>

        {/* Product showcase */}
        {isShowcase && products.length > 0 && (
          <div className="flex items-center justify-center py-8 lg:py-0">
            {products.length === 1 ? (
              /* Single product — large card */
              <Link
                href={`/products/${products[0].slug}`}
                className="group w-full max-w-md"
              >
                <div className="bg-white/10 backdrop-blur-md rounded-2xl overflow-hidden border border-white/20 shadow-2xl transition-transform duration-300 group-hover:scale-[1.02]">
                  {products[0].images?.[0] && (
                    <div className="aspect-square overflow-hidden">
                      <img
                        src={products[0].images[0]}
                        alt={products[0].title}
                        className="w-full h-full object-cover"
                      />
                    </div>
                  )}
                  <div className="p-6">
                    <h3 className="text-xl font-semibold mb-2">{products[0].title}</h3>
                    <div className="flex items-center gap-3">
                      <span className="text-2xl font-bold">
                        ${Number(products[0].price).toFixed(2)}
                      </span>
                      {products[0].compare_at_price && (
                        <span className="text-lg opacity-60 line-through">
                          ${Number(products[0].compare_at_price).toFixed(2)}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </Link>
            ) : (
              /* Multiple products — stacked/overlapping cards */
              <div className="relative w-full max-w-lg h-80 sm:h-96">
                {products.slice(0, 3).map((product, i) => (
                  <Link
                    key={product.id}
                    href={`/products/${product.slug}`}
                    className="absolute group transition-all duration-500 hover:z-30"
                    style={{
                      top: `${i * 20}px`,
                      left: `${i * 24}px`,
                      right: `${(2 - i) * 24}px`,
                      zIndex: 10 + i,
                    }}
                  >
                    <div className="bg-white/10 backdrop-blur-md rounded-xl overflow-hidden border border-white/20 shadow-xl transition-transform duration-300 group-hover:scale-[1.03]">
                      {product.images?.[0] && (
                        <div className="aspect-[4/3] overflow-hidden">
                          <img
                            src={product.images[0]}
                            alt={product.title}
                            className="w-full h-full object-cover"
                          />
                        </div>
                      )}
                      <div className="p-4 bg-black/20">
                        <h3 className="font-semibold text-sm truncate">{product.title}</h3>
                        <span className="text-lg font-bold">
                          ${Number(product.price).toFixed(2)}
                        </span>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
