/**
 * Reusable status badge component for the Super Admin Dashboard.
 *
 * Displays a colored dot and label indicating the health state
 * of a service or provider.
 *
 * For Developers:
 *   Import and use: `<StatusBadge status="healthy" />`.
 *   Accepts "healthy", "degraded", or "down" as the status prop.
 *   Optionally pass `size="sm"` for a compact variant.
 *
 * For QA Engineers:
 *   Verify that each status value renders the correct color:
 *   - healthy: green dot, green text
 *   - degraded: amber/yellow dot, amber text
 *   - down: red dot, red text
 *   - unknown: grey dot, grey text (fallback)
 *
 * For Project Managers:
 *   This component provides at-a-glance system health indicators
 *   used across the overview and services pages.
 */

"use client";

/**
 * Possible health status values for a service or provider.
 */
export type HealthStatus = "healthy" | "degraded" | "down" | "unknown";

/**
 * Props for the StatusBadge component.
 *
 * @param status - The health status to display.
 * @param size - Optional size variant: "sm" for compact, "md" for default.
 * @param label - Optional custom label text. Defaults to the status value.
 */
interface StatusBadgeProps {
  status: HealthStatus;
  size?: "sm" | "md";
  label?: string;
}

/**
 * Color configuration for each health status.
 *
 * Maps status values to their dot color, text color, and background
 * for the badge container.
 */
const STATUS_CONFIG: Record<
  HealthStatus,
  { dot: string; text: string; bg: string }
> = {
  healthy: {
    dot: "bg-[oklch(0.72_0.18_155)]",
    text: "text-[oklch(0.72_0.18_155)]",
    bg: "bg-[oklch(0.72_0.18_155_/_0.1)]",
  },
  degraded: {
    dot: "bg-[oklch(0.78_0.16_80)]",
    text: "text-[oklch(0.78_0.16_80)]",
    bg: "bg-[oklch(0.78_0.16_80_/_0.1)]",
  },
  down: {
    dot: "bg-[oklch(0.63_0.22_25)]",
    text: "text-[oklch(0.63_0.22_25)]",
    bg: "bg-[oklch(0.63_0.22_25_/_0.1)]",
  },
  unknown: {
    dot: "bg-[oklch(0.48_0.02_260)]",
    text: "text-[oklch(0.48_0.02_260)]",
    bg: "bg-[oklch(0.48_0.02_260_/_0.1)]",
  },
};

/**
 * Renders a status indicator badge with a colored dot and label.
 *
 * @param props - The component props.
 * @returns A styled badge element.
 */
export function StatusBadge({
  status,
  size = "md",
  label,
}: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.unknown;
  const displayLabel = label || status;

  const sizeClasses =
    size === "sm"
      ? "px-2 py-0.5 text-[10px] gap-1"
      : "px-2.5 py-1 text-[11px] gap-1.5";

  const dotSize = size === "sm" ? "w-1.5 h-1.5" : "w-2 h-2";

  return (
    <span
      className={`inline-flex items-center rounded-full font-medium uppercase tracking-wider ${config.bg} ${config.text} ${sizeClasses}`}
    >
      <span
        className={`${dotSize} rounded-full ${config.dot} ${
          status === "healthy" ? "animate-pulse-glow" : ""
        }`}
      />
      {displayLabel}
    </span>
  );
}
