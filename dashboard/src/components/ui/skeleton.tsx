/**
 * Skeleton loading placeholder component.
 *
 * Renders an animated shimmer effect to indicate content is loading.
 * Use instead of loading spinners or "Loading..." text for a polished UX.
 *
 * **For Developers:**
 *   - Use className to set width, height, and shape (rounded-full for circles)
 *   - Animates with a subtle pulse effect
 *   - Compose multiple skeletons to match the layout of the content being loaded
 *
 * **For QA:**
 *   - Skeletons should appear immediately when a page/section is loading
 *   - Animation should be smooth and subtle (not distracting)
 *   - Should match the approximate size of the content it replaces
 */

import { cn } from "@/lib/utils";

/**
 * Renders an animated skeleton placeholder.
 *
 * @param className - CSS classes to control size, shape, and spacing.
 * @returns A div with shimmer animation.
 */
function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton"
      className={cn("animate-pulse rounded-md bg-muted", className)}
      {...props}
    />
  );
}

export { Skeleton };
