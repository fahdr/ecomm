/**
 * Badge component for status indicators and labels.
 *
 * **For Developers:**
 *   - Variants: default (primary), secondary (muted), destructive (red), outline (bordered).
 *   - Import: `import { Badge } from "@ecomm/ui-kit"`
 *
 * **For QA Engineers:**
 *   - Verify all variant colors are distinguishable.
 *   - Check contrast ratios meet WCAG AA.
 *
 * **For End Users:**
 *   - Badges indicate status or category (e.g. "Active", "Pro Plan").
 */

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../../lib/utils";

/** CVA definition for badge style variants. */
const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground shadow",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground",
        destructive:
          "border-transparent bg-destructive text-white shadow",
        outline: "text-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

/** Props for the Badge component. */
export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

/**
 * Inline badge for status labels and categories.
 *
 * @param props - BadgeProps with variant and standard div attributes.
 * @returns A styled inline badge element.
 */
function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
