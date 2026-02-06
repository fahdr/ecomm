/**
 * Storefront homepage.
 *
 * Displays the store's hero section with name, description, and niche,
 * plus an empty product grid placeholder (products will be added in
 * Feature 5).
 *
 * If no store is resolved (missing ``?store=`` param or unknown slug),
 * a "Store not found" message is shown.
 *
 * **For Developers:**
 *   This is a server component. Store data is read from the
 *   ``x-store-slug`` header set by middleware, then fetched from the API.
 *
 * **For QA Engineers:**
 *   - With a valid slug: shows store name, description, niche, product placeholder.
 *   - Without a slug: shows "Store not found" with instructions.
 *   - With an invalid slug: shows "Store not found".
 *
 * **For End Users:**
 *   This is the main page of your store. Customers see your store name,
 *   description, and products here.
 */

import { headers } from "next/headers";
import { notFound } from "next/navigation";
import { fetchStore } from "@/lib/store";

/**
 * Homepage server component.
 *
 * @returns The store homepage with hero section and product grid placeholder.
 */
export default async function HomePage() {
  const headersList = await headers();
  const slug = headersList.get("x-store-slug");

  if (!slug) {
    notFound();
  }

  const store = await fetchStore(slug);

  if (!store) {
    notFound();
  }

  return (
    <div>
      {/* Hero Section */}
      <section className="bg-zinc-50 dark:bg-zinc-900 py-16 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Welcome to {store.name}
          </h2>
          {store.description && (
            <p className="mt-4 text-lg text-zinc-600 dark:text-zinc-400 max-w-2xl mx-auto">
              {store.description}
            </p>
          )}
          <div className="mt-6">
            <span className="inline-flex items-center rounded-full bg-zinc-200 dark:bg-zinc-700 px-3 py-1 text-sm font-medium text-zinc-700 dark:text-zinc-300">
              {store.niche}
            </span>
          </div>
        </div>
      </section>

      {/* Product Grid Placeholder */}
      <section className="py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h3 className="text-2xl font-bold tracking-tight mb-8">Products</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 p-6 flex flex-col items-center justify-center h-64"
              >
                <div className="w-16 h-16 rounded-full bg-zinc-200 dark:bg-zinc-700 mb-4" />
                <p className="text-sm text-zinc-400 dark:text-zinc-500">
                  Coming soon
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
