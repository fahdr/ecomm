/**
 * 404 / Store Not Found page.
 *
 * Displayed when the storefront cannot resolve a store from the URL.
 * This happens when:
 * - No ``?store=`` query parameter is provided (local dev)
 * - The slug doesn't match any active store in the database
 * - The store has been paused or deleted
 *
 * **For QA Engineers:**
 *   - Visiting ``localhost:3001`` without ``?store=`` shows this page.
 *   - Visiting ``localhost:3001?store=nonexistent`` shows this page.
 *   - Visiting with a paused/deleted store slug shows this page.
 *
 * **For End Users:**
 *   If you see this page, the store URL may be incorrect or the store
 *   may no longer be available.
 */

/**
 * Not Found page component.
 *
 * @returns A centered message indicating the store was not found.
 */
export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="text-center">
        <h2 className="text-6xl font-bold text-zinc-300 dark:text-zinc-700">
          404
        </h2>
        <h3 className="mt-4 text-2xl font-semibold tracking-tight">
          Store not found
        </h3>
        <p className="mt-2 text-zinc-600 dark:text-zinc-400 max-w-md">
          The store you&apos;re looking for doesn&apos;t exist or is no longer
          available. Please check the URL and try again.
        </p>
      </div>
    </div>
  );
}
