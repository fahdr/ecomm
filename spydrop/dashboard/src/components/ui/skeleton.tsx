/**
 * Skeleton loading placeholder component.
 *
 * Displays a pulsing placeholder shape that indicates content is loading.
 * Use in place of real content while API data is being fetched.
 *
 * **For Developers:**
 *   - Apply width/height via className (e.g. `h-4 w-32` for a text line).
 *   - The pulse animation uses the `animate-pulse` Tailwind utility.
 *   - Compose multiple Skeletons to match the layout of the final content.
 *   - Import: `import { Skeleton } from "@/components/ui/skeleton"`
 *
 * **For QA Engineers:**
 *   - Verify skeletons appear during loading states (throttle network in DevTools).
 *   - Check that skeleton dimensions roughly match the content they replace.
 *   - Verify the pulse animation is smooth and not jarring.
 *
 * **For End Users:**
 *   - Pulsing gray shapes indicate that data is being loaded.
 */

import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Skeleton placeholder with a pulsing animation.
 *
 * @param props - Standard div props; use className for sizing.
 * @returns A div with muted background and pulse animation.
 *
 * @example
 * // Text line skeleton
 * <Skeleton className="h-4 w-48" />
 *
 * // Card skeleton
 * <Skeleton className="h-32 w-full rounded-xl" />
 *
 * // Avatar skeleton
 * <Skeleton className="size-10 rounded-full" />
 */
function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-muted", className)}
      {...props}
    />
  );
}

export { Skeleton };
