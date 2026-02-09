/**
 * Reusable animation wrapper components using the motion library.
 *
 * Provides consistent, delightful animations across the dashboard:
 * - FadeIn: fade + slide up on mount
 * - StaggerChildren: container that staggers child animations
 * - PageTransition: wrapper for page-level fade transitions
 *
 * **For Developers:**
 *   - All wrappers use motion/react (formerly framer-motion)
 *   - FadeIn accepts custom delay, duration, and direction
 *   - StaggerChildren automatically staggers direct children
 *   - Use these to wrap page content and card grids
 *
 * **For QA:**
 *   - Animations should play on page load / component mount
 *   - Staggered grids should reveal cards sequentially
 *   - Animations should respect prefers-reduced-motion
 */

"use client";

import { motion, type HTMLMotionProps } from "motion/react";

/**
 * Props for the FadeIn animation wrapper.
 */
interface FadeInProps extends HTMLMotionProps<"div"> {
  /** Delay before animation starts, in seconds. Default: 0 */
  delay?: number;
  /** Animation duration in seconds. Default: 0.4 */
  duration?: number;
  /** Direction to slide from. Default: "up" */
  direction?: "up" | "down" | "left" | "right" | "none";
  /** Distance to slide in pixels. Default: 12 */
  distance?: number;
}

/**
 * Wraps children in a fade + slide animation on mount.
 *
 * @param delay - Delay in seconds before animation starts.
 * @param duration - Animation duration in seconds.
 * @param direction - Direction to slide from ("up", "down", "left", "right", "none").
 * @param distance - Slide distance in pixels.
 * @param children - Content to animate.
 * @returns A motion div with entrance animation.
 */
export function FadeIn({
  delay = 0,
  duration = 0.4,
  direction = "up",
  distance = 12,
  children,
  ...props
}: FadeInProps) {
  const directionMap = {
    up: { y: distance },
    down: { y: -distance },
    left: { x: distance },
    right: { x: -distance },
    none: {},
  };

  return (
    <motion.div
      initial={{ opacity: 0, ...directionMap[direction] }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      transition={{
        duration,
        delay,
        ease: [0.25, 0.1, 0.25, 1],
      }}
      {...props}
    >
      {children}
    </motion.div>
  );
}

/**
 * Container that staggers the entrance animation of its direct children.
 *
 * Each child gets a sequential delay for a cascading reveal effect.
 * Works best with FadeIn children, but can wrap any elements.
 *
 * @param staggerDelay - Delay between each child in seconds. Default: 0.08
 * @param children - Direct children to stagger.
 * @returns A motion div with staggered child animations.
 */
export function StaggerChildren({
  staggerDelay = 0.08,
  children,
  className,
  ...props
}: {
  staggerDelay?: number;
  children: React.ReactNode;
  className?: string;
} & HTMLMotionProps<"div">) {
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={{
        hidden: {},
        visible: {
          transition: {
            staggerChildren: staggerDelay,
          },
        },
      }}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  );
}

/**
 * Motion variant for use inside StaggerChildren.
 *
 * Apply as variants={{ hidden: staggerItem.hidden, visible: staggerItem.visible }}
 * on motion elements that are direct children of StaggerChildren.
 */
export const staggerItem = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.4,
      ease: [0.25, 0.1, 0.25, 1] as [number, number, number, number],
    },
  },
};

/**
 * Wrapper for page-level fade transitions.
 *
 * Use this to wrap the main content of each page for a consistent
 * entrance animation.
 *
 * @param children - Page content to animate.
 * @returns A motion div with page fade-in animation.
 */
export function PageTransition({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.35,
        ease: [0.25, 0.1, 0.25, 1],
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
