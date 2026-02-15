/**
 * Motion primitives -- reusable animation components built on the ``motion``
 * library for consistent, performant animations across the storefront.
 *
 * **For Developers:**
 *   Import these components to add entrance animations to any section.
 *   All primitives are client components. They use the ``motion/react``
 *   API with IntersectionObserver-based triggers for scroll-reveal.
 *
 *   Available components:
 *   - ``FadeIn``         — Opacity 0→1 with optional translateY.
 *   - ``StaggerChildren`` — Wraps children with staggered delays.
 *   - ``SlideIn``         — Slides from a direction (left/right/bottom).
 *   - ``ScaleIn``         — Scale 0.95→1 with opacity.
 *   - ``ScrollReveal``    — Triggers animation when element enters viewport.
 *
 * **For QA Engineers:**
 *   - Animations only trigger once (``once: true`` on viewport triggers).
 *   - Reduced-motion preference is respected via ``motion`` defaults.
 *   - Delay values are in seconds.
 *
 * **For End Users:**
 *   Smooth entrance animations that make browsing feel premium.
 *
 * @module components/motion-primitives
 */

"use client";

import { type ReactNode } from "react";
import { motion, useInView, stagger, useAnimate } from "motion/react";
import { useRef, useEffect } from "react";

/** Common animation props. */
interface MotionProps {
  children: ReactNode;
  /** Delay in seconds before the animation starts. */
  delay?: number;
  /** Duration in seconds. Default 0.5. */
  duration?: number;
  /** Additional CSS class names. */
  className?: string;
}

/**
 * Fade in from transparent with optional vertical translate.
 *
 * @param props - Component props.
 * @returns Animated wrapper div.
 */
export function FadeIn({ children, delay = 0, duration = 0.5, className = "" }: MotionProps) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-50px" });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 20 }}
      animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
      transition={{ duration, delay, ease: "easeOut" }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/** Direction for SlideIn. */
type SlideDirection = "left" | "right" | "bottom" | "top";

interface SlideInProps extends MotionProps {
  /** Direction to slide from. Default "bottom". */
  from?: SlideDirection;
  /** Distance in pixels. Default 40. */
  distance?: number;
}

/**
 * Slide in from a specified direction.
 *
 * @param props - Component props.
 * @returns Animated wrapper div.
 */
export function SlideIn({
  children,
  from = "bottom",
  distance = 40,
  delay = 0,
  duration = 0.6,
  className = "",
}: SlideInProps) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-50px" });

  const initialOffset = {
    left: { x: -distance, y: 0 },
    right: { x: distance, y: 0 },
    bottom: { x: 0, y: distance },
    top: { x: 0, y: -distance },
  }[from];

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, ...initialOffset }}
      animate={isInView ? { opacity: 1, x: 0, y: 0 } : { opacity: 0, ...initialOffset }}
      transition={{ duration, delay, ease: "easeOut" }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/**
 * Scale in from 0.95 to 1 with opacity fade.
 *
 * @param props - Component props.
 * @returns Animated wrapper div.
 */
export function ScaleIn({ children, delay = 0, duration = 0.5, className = "" }: MotionProps) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-50px" });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={isInView ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.95 }}
      transition={{ duration, delay, ease: "easeOut" }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

interface StaggerChildrenProps {
  children: ReactNode;
  /** Delay between each child in seconds. Default 0.08. */
  staggerDelay?: number;
  /** Additional CSS class names. */
  className?: string;
}

/**
 * Wraps children with staggered entrance animations.
 * Each direct child element fades in with an incremental delay.
 *
 * @param props - Component props.
 * @returns Container div with staggered animated children.
 */
export function StaggerChildren({
  children,
  staggerDelay = 0.08,
  className = "",
}: StaggerChildrenProps) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-30px" });

  return (
    <motion.div
      ref={ref}
      initial="hidden"
      animate={isInView ? "visible" : "hidden"}
      variants={{
        hidden: {},
        visible: {
          transition: {
            staggerChildren: staggerDelay,
          },
        },
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/**
 * A child variant for use inside StaggerChildren.
 * Fades in with upward translate.
 */
export const staggerItem = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, ease: "easeOut" as const },
  },
};

/** Props for individual stagger items. */
interface StaggerItemProps {
  children: ReactNode;
  className?: string;
}

/**
 * A single animated item to place inside a StaggerChildren container.
 *
 * @param props - Component props.
 * @returns A motion.div with stagger item variants.
 */
export function StaggerItem({ children, className = "" }: StaggerItemProps) {
  return (
    <motion.div variants={staggerItem} className={className}>
      {children}
    </motion.div>
  );
}

interface ScrollRevealProps extends MotionProps {
  /** Animation type. Default "fade". */
  type?: "fade" | "slide-up" | "scale";
}

/**
 * Triggers an animation when the element enters the viewport.
 * A more configurable version of FadeIn for varied reveal styles.
 *
 * @param props - Component props.
 * @returns Animated wrapper div.
 */
export function ScrollReveal({
  children,
  type = "fade",
  delay = 0,
  duration = 0.6,
  className = "",
}: ScrollRevealProps) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  const variants = {
    fade: {
      initial: { opacity: 0 },
      animate: { opacity: 1 },
    },
    "slide-up": {
      initial: { opacity: 0, y: 30 },
      animate: { opacity: 1, y: 0 },
    },
    scale: {
      initial: { opacity: 0, scale: 0.9 },
      animate: { opacity: 1, scale: 1 },
    },
  };

  const v = variants[type];

  return (
    <motion.div
      ref={ref}
      initial={v.initial}
      animate={isInView ? v.animate : v.initial}
      transition={{ duration, delay, ease: "easeOut" }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
