/**
 * Category listing page for the storefront.
 *
 * Displays all active categories for the current store in a visually
 * rich grid layout. Each category card links to its products page.
 *
 * **For Developers:**
 *   This is a server component. The store slug comes from the
 *   ``x-store-slug`` header set by middleware. Categories are fetched
 *   from the public API endpoint.
 *
 * **For QA Engineers:**
 *   - Only active categories from active stores are shown.
 *   - Categories without products still appear but show "0 products".
 *   - Visiting without a valid store slug shows 404.
 *   - Categories are sorted by position then name.
 *
 * **For End Users:**
 *   Browse product categories to find what you are looking for. Click
 *   any category to see all products within it.
 */

import { headers } from "next/headers";
import { notFound } from "next/navigation";
import Link from "next/link";
import { fetchStore } from "@/lib/store";
import { api } from "@/lib/api";
import type { Category } from "@/lib/types";

/**
 * Categories listing page server component.
 *
 * @returns A page displaying all store categories in a grid.
 */
export default async function CategoriesPage() {
  const headersList = await headers();
  const slug = headersList.get("x-store-slug");

  if (!slug) {
    notFound();
  }

  const store = await fetchStore(slug);
  if (!store) {
    notFound();
  }

  const { data: categories } = await api.get<Category[]>(
    `/api/v1/public/stores/${encodeURIComponent(slug)}/categories`
  );

  const allCategories = categories ?? [];

  /* Separate top-level categories from subcategories for structured display. */
  const topLevel = allCategories.filter((c) => !c.parent_id);
  const children = allCategories.filter((c) => c.parent_id);

  return (
    <div className="py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Page header */}
        <div className="mb-10">
          <h2 className="text-3xl font-bold tracking-tight">Categories</h2>
          <p className="mt-2 text-zinc-500 dark:text-zinc-400">
            Browse our collections to find exactly what you need.
          </p>
        </div>

        {topLevel.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-zinc-500 dark:text-zinc-400">
              No categories available yet. Check back soon!
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {topLevel.map((category, index) => {
              /* Find subcategories belonging to this parent. */
              const subs = children.filter((c) => c.parent_id === category.id);

              return (
                <CategoryCard
                  key={category.id}
                  category={category}
                  subcategories={subs}
                  index={index}
                />
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Individual category card with hover effect and subcategory chips.
 *
 * @param props - Component props.
 * @param props.category - The parent category data.
 * @param props.subcategories - Child categories nested under this one.
 * @param props.index - Position index for staggered entrance animation.
 * @returns A card linking to the category products page.
 */
function CategoryCard({
  category,
  subcategories,
  index,
}: {
  category: Category;
  subcategories: Category[];
  index: number;
}) {
  /*
   * A palette of accent colours rotated through the category cards.
   * Uses warm/earthy tones inspired by department store signage rather
   * than the cliched purple-gradient AI aesthetic.
   */
  const accents = [
    "from-amber-600/20 to-orange-600/10 border-amber-500/30",
    "from-teal-600/20 to-emerald-600/10 border-teal-500/30",
    "from-rose-600/20 to-pink-600/10 border-rose-500/30",
    "from-sky-600/20 to-blue-600/10 border-sky-500/30",
    "from-violet-600/20 to-fuchsia-600/10 border-violet-500/30",
    "from-lime-600/20 to-green-600/10 border-lime-500/30",
  ];
  const accent = accents[index % accents.length];

  return (
    <Link
      href={`/categories/${category.slug}`}
      className="group block"
      style={{ animationDelay: `${index * 80}ms` }}
    >
      <div
        className={`relative overflow-hidden rounded-xl border bg-gradient-to-br ${accent} p-6 transition-all duration-300 hover:shadow-lg hover:-translate-y-0.5`}
      >
        {/* Product count badge */}
        <span className="absolute top-4 right-4 inline-flex items-center rounded-full bg-white/80 dark:bg-zinc-900/80 px-2.5 py-0.5 text-xs font-medium backdrop-blur-sm">
          {category.product_count} product{category.product_count !== 1 ? "s" : ""}
        </span>

        {/* Category name */}
        <h3 className="text-xl font-semibold tracking-tight mb-2 group-hover:underline decoration-2 underline-offset-4">
          {category.name}
        </h3>

        {/* Description */}
        {category.description && (
          <p className="text-sm text-zinc-600 dark:text-zinc-400 line-clamp-2 mb-4">
            {category.description}
          </p>
        )}

        {/* Subcategory chips */}
        {subcategories.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {subcategories.slice(0, 4).map((sub) => (
              <span
                key={sub.id}
                className="inline-block rounded-md bg-white/60 dark:bg-zinc-800/60 px-2 py-0.5 text-xs text-zinc-600 dark:text-zinc-300"
              >
                {sub.name}
              </span>
            ))}
            {subcategories.length > 4 && (
              <span className="inline-block rounded-md bg-white/60 dark:bg-zinc-800/60 px-2 py-0.5 text-xs text-zinc-500 dark:text-zinc-400">
                +{subcategories.length - 4} more
              </span>
            )}
          </div>
        )}

        {/* Arrow indicator */}
        <div className="mt-4 text-sm font-medium text-zinc-700 dark:text-zinc-300 group-hover:translate-x-1 transition-transform">
          Browse products &rarr;
        </div>
      </div>
    </Link>
  );
}
