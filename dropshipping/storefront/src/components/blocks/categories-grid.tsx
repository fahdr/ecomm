/**
 * Categories Grid block -- a client-side grid of category cards fetched
 * from the store's public API.
 *
 * Renders all top-level categories for the store in a responsive card
 * layout.  Each card shows the category name, description, product count,
 * and an optional image.  Clicking a card navigates to that category's
 * product listing page.
 *
 * **For Developers:**
 *   This is a **client component** (``"use client"``).  Categories are
 *   fetched on mount from ``GET /api/v1/public/stores/{slug}/categories``.
 *   The ``columns`` config value controls the grid layout (default 3).
 *   The store slug is obtained from the ``useStore()`` context hook.
 *
 * **For QA Engineers:**
 *   - If the store context is null, the block renders nothing.
 *   - If the API returns an error or empty list, a "no categories" message
 *     is displayed.
 *   - Categories without images show a gradient placeholder using theme
 *     colors.
 *   - Product count is shown as a badge on each card.
 *   - ``columns`` defaults to 3 when unspecified.
 *   - Loading state displays animated skeleton cards.
 *
 * **For Project Managers:**
 *   Store owners can organise products into categories via the dashboard.
 *   This block automatically displays those categories on the homepage so
 *   customers can browse by topic.  Grid column count is configurable
 *   through the theme editor.
 *
 * **For End Users:**
 *   Browse product categories to quickly find what you are looking for.
 *   Click a category card to see all products in that category.
 *
 * @module blocks/categories-grid
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useStore } from "@/contexts/store-context";
import type { Category } from "@/lib/types";

/**
 * Props accepted by the {@link CategoriesGrid} component.
 */
interface CategoriesGridProps {
  /**
   * Block configuration object.  Expected keys:
   * - ``columns`` (number) -- Number of grid columns on large screens (default 3).
   */
  config: Record<string, unknown>;
}

/**
 * Map a column count to the corresponding Tailwind grid-cols class for the
 * ``lg`` breakpoint.
 *
 * @param cols - Desired number of columns (2--6).
 * @returns A Tailwind ``lg:grid-cols-*`` class string.
 */
function gridColsClass(cols: number): string {
  const map: Record<number, string> = {
    2: "lg:grid-cols-2",
    3: "lg:grid-cols-3",
    4: "lg:grid-cols-4",
    5: "lg:grid-cols-5",
    6: "lg:grid-cols-6",
  };
  return map[cols] || "lg:grid-cols-3";
}

/**
 * Render a grid of category cards fetched from the public API.
 *
 * @param props - Component props.
 * @param props.config - Block configuration from the store theme.
 * @returns A section with a category grid, loading skeleton, or empty state.
 */
export function CategoriesGrid({ config }: CategoriesGridProps) {
  const store = useStore();
  const columns = typeof config.columns === "number" ? config.columns : 3;

  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);

  /**
   * Fetch categories from the public API on component mount.
   */
  useEffect(() => {
    if (!store) {
      setLoading(false);
      return;
    }

    let cancelled = false;

    async function fetchCategories() {
      const { data } = await api.get<Category[]>(
        `/api/v1/public/stores/${encodeURIComponent(store!.slug)}/categories`
      );
      if (!cancelled && data) {
        setCategories(data);
      }
      if (!cancelled) {
        setLoading(false);
      }
    }

    fetchCategories();
    return () => {
      cancelled = true;
    };
  }, [store]);

  // Don't render anything if no store context is available
  if (!store) return null;

  return (
    <section className="mx-auto max-w-7xl px-6 py-16">
      <h2 className="font-heading text-3xl font-bold tracking-tight mb-8 text-center">
        Shop by Category
      </h2>

      {/* Loading skeleton */}
      {loading && (
        <div className={`grid grid-cols-1 sm:grid-cols-2 ${gridColsClass(columns)} gap-6`}>
          {Array.from({ length: columns }).map((_, i) => (
            <div key={i} className="theme-card overflow-hidden animate-pulse">
              <div className="aspect-3/2 bg-theme-border" />
              <div className="p-5 space-y-3">
                <div className="h-5 rounded bg-theme-border w-1/2" />
                <div className="h-4 rounded bg-theme-border w-3/4" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && categories.length === 0 && (
        <div className="text-center py-12">
          <p className="text-theme-muted">
            No categories available yet. Check back soon!
          </p>
        </div>
      )}

      {/* Categories grid */}
      {!loading && categories.length > 0 && (
        <div className={`grid grid-cols-1 sm:grid-cols-2 ${gridColsClass(columns)} gap-6`}>
          {categories.map((category) => (
            <CategoryCard key={category.id} category={category} />
          ))}
        </div>
      )}
    </section>
  );
}

/**
 * Individual category card within the categories grid.
 *
 * Displays a category image (or a gradient placeholder), name, optional
 * description, and the number of products in that category.
 *
 * @param props - Component props.
 * @param props.category - The category data to render.
 * @returns A linked card element for the category.
 */
function CategoryCard({ category }: { category: Category }) {
  return (
    <Link href={`/categories/${category.slug}`} className="group">
      <div className="theme-card overflow-hidden">
        {/* Category image or gradient placeholder */}
        <div className="aspect-3/2 overflow-hidden relative">
          {category.image_url ? (
            <img
              src={category.image_url}
              alt={category.name}
              className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
              loading="lazy"
            />
          ) : (
            <div
              className="h-full w-full flex items-center justify-center"
              style={{
                background:
                  "linear-gradient(135deg, var(--theme-primary) 0%, var(--theme-accent) 100%)",
              }}
            >
              <span
                className="text-4xl font-bold opacity-30"
                style={{ color: "var(--theme-primary-text)" }}
              >
                {category.name.charAt(0).toUpperCase()}
              </span>
            </div>
          )}
        </div>

        {/* Category info */}
        <div className="p-5">
          <div className="flex items-center justify-between mb-1">
            <h3 className="font-heading font-semibold text-lg">
              {category.name}
            </h3>
            <span className="text-xs font-medium text-theme-muted bg-theme-surface border border-theme px-2 py-0.5 rounded-full">
              {category.product_count} product{category.product_count !== 1 ? "s" : ""}
            </span>
          </div>
          {category.description && (
            <p className="text-sm text-theme-muted line-clamp-2 mt-1">
              {category.description}
            </p>
          )}
        </div>
      </div>
    </Link>
  );
}
