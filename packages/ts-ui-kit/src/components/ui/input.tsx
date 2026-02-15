/**
 * Input component for text, email, password, and other form fields.
 *
 * **For Developers:**
 *   - Styled to match the card/border theme with consistent height (h-9).
 *   - Includes focus ring using the primary color via --ring CSS variable.
 *   - Supports all native input attributes (type, placeholder, disabled, etc.).
 *
 * **For QA Engineers:**
 *   - Test with various input types (text, email, password, number).
 *   - Verify placeholder text has sufficient contrast.
 *   - Check disabled state renders with reduced opacity.
 *
 * **For End Users:**
 *   - Form fields highlight with the service accent color when focused.
 */

import * as React from "react";
import { cn } from "../../lib/utils";

/** Props for the Input component (extends native input attributes). */
export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

/**
 * Styled text input with consistent theming and focus behavior.
 *
 * @param props - Standard HTML input attributes plus className override.
 * @returns A themed input element.
 *
 * @example
 * <Input type="email" placeholder="you@example.com" value={email} onChange={...} />
 */
const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input };
