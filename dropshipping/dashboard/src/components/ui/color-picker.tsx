/**
 * Color picker component for theme customization.
 *
 * Combines a native ``<input type="color">`` with a hex text input
 * and color swatch preview for precise color selection.
 *
 * **For Developers:**
 *   Controlled component — parent manages the color state via
 *   ``value`` and ``onChange``. Hex values include the ``#`` prefix.
 *
 * **For End Users:**
 *   Click the color swatch to open a visual picker, or type a hex
 *   code directly (e.g. ``#0d9488``).
 *
 * @param props - Component props.
 * @param props.label - Descriptive label for this color role (e.g. "Primary").
 * @param props.value - Current hex color string (e.g. "#0d9488").
 * @param props.onChange - Callback fired when the color changes.
 * @returns A color picker with swatch, native picker, and text input.
 */
"use client";

interface ColorPickerProps {
  /** Label for the color role (e.g. "Primary", "Accent"). */
  label: string;
  /** Current hex color value. */
  value: string;
  /** Called when the color changes. */
  onChange: (value: string) => void;
}

export function ColorPicker({ label, value, onChange }: ColorPickerProps) {
  return (
    <div className="flex items-center gap-3">
      <div className="relative">
        <div
          className="h-9 w-9 rounded-lg border border-border shadow-sm cursor-pointer"
          style={{ backgroundColor: value }}
        />
        <input
          type="color"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="absolute inset-0 opacity-0 cursor-pointer h-9 w-9"
          aria-label={`Pick ${label} color`}
        />
      </div>
      <div className="flex-1 min-w-0">
        <label className="text-xs font-medium text-muted-foreground block mb-1">
          {label}
        </label>
        <input
          type="text"
          value={value}
          onChange={(e) => {
            const v = e.target.value;
            if (/^#[0-9a-fA-F]{0,6}$/.test(v)) {
              onChange(v);
            }
          }}
          className="w-full rounded-md border border-border bg-background px-2 py-1 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-primary"
          placeholder="#000000"
          maxLength={7}
        />
      </div>
    </div>
  );
}
