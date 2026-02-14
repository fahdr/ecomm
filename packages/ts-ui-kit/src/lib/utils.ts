/**
 * Shared utility functions used throughout all ecomm SaaS dashboards.
 *
 * **For Developers:**
 *   - `cn()` merges Tailwind class names with proper precedence using
 *     clsx (conditional joining) + tailwind-merge (deduplication).
 *   - Import as: `import { cn } from "@ecomm/ui-kit/lib/utils"`
 */

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge CSS class names with Tailwind-aware deduplication.
 *
 * Combines clsx (for conditional class joining) with tailwind-merge
 * (which resolves conflicting Tailwind utility classes by keeping
 * only the last one).
 *
 * @param inputs - Any number of class values (strings, arrays, objects, undefined).
 * @returns A single, deduplicated class string.
 *
 * @example
 * cn("px-4 py-2", isActive && "bg-primary", "px-6")
 * // => "py-2 px-6 bg-primary"  (px-4 is overridden by px-6)
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
