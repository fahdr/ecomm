/**
 * Button component with multiple visual variants and sizes.
 *
 * Uses class-variance-authority (CVA) for type-safe variant management
 * and tailwind-merge for clean class composition.
 *
 * **For Developers:**
 *   - Variants: default (primary fill), outline (bordered), ghost (transparent),
 *     destructive (red fill), secondary (muted fill), link (underline).
 *   - Sizes: default (h-9), sm (h-8), lg (h-10), icon (square 9x9).
 *   - Supports `asChild` prop via Radix Slot for composing with Link or other elements.
 *   - Active state includes a subtle scale-down (0.97) for tactile feedback.
 *
 * **For QA Engineers:**
 *   - Verify all variant/size combinations render distinctly.
 *   - Check disabled state removes pointer events and reduces opacity.
 *   - Test keyboard navigation (Enter/Space triggers click).
 *   - Verify focus ring is visible in both light and dark mode.
 *
 * **For End Users:**
 *   - Buttons provide visual feedback on hover and click.
 *   - Disabled buttons appear faded and cannot be clicked.
 */

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { Slot } from "@radix-ui/react-slot";
import { cn } from "@/lib/utils";

/**
 * CVA definition for button style variants.
 * Base styles include flex layout, rounded corners, transitions, and focus ring.
 */
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all duration-150 active:scale-[0.97] disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background cursor-pointer",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground shadow-sm hover:bg-primary/90",
        destructive:
          "bg-destructive text-white shadow-sm hover:bg-destructive/90",
        outline:
          "border border-input bg-background shadow-xs hover:bg-secondary hover:text-secondary-foreground",
        secondary:
          "bg-secondary text-secondary-foreground shadow-xs hover:bg-secondary/80",
        ghost:
          "hover:bg-secondary hover:text-secondary-foreground",
        link:
          "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-md px-6",
        icon: "size-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

/** Props for the Button component, extending native button props with CVA variants. */
export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  /**
   * When true, the Button renders as a Radix Slot, merging its props
   * onto the immediate child element. Useful for wrapping Next.js Link.
   */
  asChild?: boolean;
}

/**
 * Polymorphic button component with variant-based styling.
 *
 * @param props - ButtonProps including variant, size, asChild, and standard button attrs.
 * @returns A styled button (or Slot child if asChild is true).
 *
 * @example
 * <Button variant="default" size="lg" onClick={handleSave}>
 *   Save Changes
 * </Button>
 *
 * @example
 * <Button variant="outline" asChild>
 *   <Link href="/settings">Settings</Link>
 * </Button>
 */
const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
