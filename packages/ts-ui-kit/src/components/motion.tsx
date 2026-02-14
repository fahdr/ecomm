/**
 * Animation wrapper components using the `motion` library (v12+).
 *
 * These composable primitives provide consistent entrance animations
 * throughout all ecomm SaaS dashboards. They use the motion library
 * (formerly framer-motion) for spring-based, GPU-accelerated animations.
 *
 * **For Developers:**
 *   - `FadeIn` — fades in from a configurable direction (up, down, left, right, none).
 *   - `StaggerChildren` — staggers the entrance of its direct children.
 *   - `PageTransition` — full-page fade+slide for route transitions.
 *   - `AnimatedCounter` — smooth count-up effect for KPI numbers.
 *   - Import from: `import { FadeIn, StaggerChildren } from "@ecomm/ui-kit"`
 *
 * **For QA Engineers:**
 *   - Animations should be smooth at 60fps — check for jank in Performance tab.
 *   - Verify that reduced-motion preference disables animations.
 *
 * **For End Users:**
 *   - Elements gracefully animate into view as you navigate the dashboard.
 */

"use client";

import * as React from "react";
import * as motion from "motion/react-client";

/** Direction from which the FadeIn animation originates. */
type FadeDirection = "up" | "down" | "left" | "right" | "none";

/** Props for the FadeIn animation wrapper. */
interface FadeInProps {
  /** Direction the element slides in from. Default: "up". */
  direction?: FadeDirection;
  /** Delay before the animation starts, in seconds. Default: 0. */
  delay?: number;
  /** Duration of the animation in seconds. Default: 0.5. */
  duration?: number;
  /** Additional CSS classes. */
  className?: string;
  /** Child elements to animate. */
  children: React.ReactNode;
}

/**
 * Compute the initial transform offset based on the fade direction.
 *
 * @param direction - The direction to slide in from.
 * @returns An object with x and y offsets.
 */
function getDirectionOffset(direction: FadeDirection): { x: number; y: number } {
  switch (direction) {
    case "up":
      return { x: 0, y: 20 };
    case "down":
      return { x: 0, y: -20 };
    case "left":
      return { x: 20, y: 0 };
    case "right":
      return { x: -20, y: 0 };
    case "none":
      return { x: 0, y: 0 };
  }
}

/**
 * Fade-in animation wrapper with configurable direction and timing.
 *
 * @param props - FadeInProps.
 * @returns An animated div wrapping the children.
 *
 * @example
 * <FadeIn direction="up" delay={0.1}>
 *   <Card>Content here</Card>
 * </FadeIn>
 */
export function FadeIn({
  direction = "up",
  delay = 0,
  duration = 0.5,
  className,
  children,
}: FadeInProps) {
  const offset = getDirectionOffset(direction);

  return (
    <motion.div
      initial={{ opacity: 0, x: offset.x, y: offset.y }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      transition={{
        duration,
        delay,
        ease: [0.25, 0.46, 0.45, 0.94],
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/** Props for the StaggerChildren animation container. */
interface StaggerChildrenProps {
  /** Delay between each child animation in seconds. Default: 0.08. */
  staggerDelay?: number;
  /** Initial delay before the first child animates. Default: 0. */
  delay?: number;
  /** Additional CSS classes for the container div. */
  className?: string;
  /** Child elements to stagger. */
  children: React.ReactNode;
}

/**
 * Container that staggers the entrance animation of its direct children.
 *
 * @param props - StaggerChildrenProps.
 * @returns A div whose children animate in sequence.
 *
 * @example
 * <StaggerChildren staggerDelay={0.1}>
 *   <Card>First</Card>
 *   <Card>Second</Card>
 * </StaggerChildren>
 */
export function StaggerChildren({
  staggerDelay = 0.08,
  delay = 0,
  className,
  children,
}: StaggerChildrenProps) {
  return (
    <div className={className}>
      {React.Children.map(children, (child, index) => (
        <motion.div
          key={index}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            duration: 0.4,
            delay: delay + index * staggerDelay,
            ease: [0.25, 0.46, 0.45, 0.94],
          }}
        >
          {child}
        </motion.div>
      ))}
    </div>
  );
}

/** Props for the PageTransition wrapper. */
interface PageTransitionProps {
  /** Additional CSS classes. */
  className?: string;
  /** Page content to animate. */
  children: React.ReactNode;
}

/**
 * Full-page transition wrapper that fades and slides content in.
 *
 * @param props - PageTransitionProps.
 * @returns An animated div wrapping the page content.
 */
export function PageTransition({ className, children }: PageTransitionProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/** Props for the AnimatedCounter component. */
interface AnimatedCounterProps {
  /** The target number to count up to. */
  value: number;
  /** Duration of the count-up animation in milliseconds. Default: 1200. */
  duration?: number;
  /** Optional formatting function (e.g. for currency, percentages). */
  formatter?: (value: number) => string;
  /** Additional CSS classes for the span element. */
  className?: string;
}

/**
 * Animated number counter that smoothly counts up from 0 to the target value.
 * Uses requestAnimationFrame for smooth 60fps counting with an ease-out curve.
 *
 * @param props - AnimatedCounterProps.
 * @returns A span element displaying the animated number.
 *
 * @example
 * <AnimatedCounter
 *   value={1284}
 *   formatter={(v) => v.toLocaleString()}
 *   className="text-3xl font-bold"
 * />
 */
export function AnimatedCounter({
  value,
  duration = 1200,
  formatter,
  className,
}: AnimatedCounterProps) {
  const [displayValue, setDisplayValue] = React.useState(0);
  const startTimeRef = React.useRef<number | null>(null);
  const rafRef = React.useRef<number>(undefined);

  React.useEffect(() => {
    startTimeRef.current = null;

    function animate(timestamp: number) {
      if (startTimeRef.current === null) {
        startTimeRef.current = timestamp;
      }

      const elapsed = timestamp - startTimeRef.current;
      const progress = Math.min(elapsed / duration, 1);

      /* Ease-out cubic curve for natural deceleration */
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayValue(Math.round(eased * value));

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate);
      }
    }

    rafRef.current = requestAnimationFrame(animate);

    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, [value, duration]);

  const formatted = formatter ? formatter(displayValue) : String(displayValue);

  return <span className={className}>{formatted}</span>;
}
