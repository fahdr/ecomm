/**
 * Countdown Timer block -- a live countdown to a target date/time,
 * perfect for product launches, flash sales, or seasonal events.
 *
 * **For Developers:**
 *   This is a **client component** with a 1-second interval timer.  Config:
 *   - ``target_date`` (string) -- ISO 8601 date string to count down to.
 *   - ``title``       (string) -- Heading text (default "Sale Ends In").
 *   - ``subtitle``    (string) -- Secondary text below the heading.
 *   - ``cta_text``    (string) -- Button label (default "Shop the Sale").
 *   - ``cta_link``    (string) -- Button URL (default "/products").
 *   - ``bg_style``    (string) -- "gradient" | "solid" | "transparent" (default "gradient").
 *
 * **For QA Engineers:**
 *   - Timer updates every second with days, hours, minutes, seconds.
 *   - When the target date has passed, the block shows "Event has ended".
 *   - Numbers should always be zero-padded (e.g. 09, 04).
 *   - Missing ``target_date`` renders nothing (block is skipped).
 *
 * **For End Users:**
 *   A countdown timer showing how much time is left for a special offer.
 *
 * @module blocks/countdown-timer
 */

"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

/** Time remaining broken down into units. */
interface TimeLeft {
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
}

/** Props for the {@link CountdownTimer} component. */
interface CountdownTimerProps {
  config: Record<string, unknown>;
}

/**
 * Calculate the time remaining until a target date.
 * @param targetDate - The target Date object.
 * @returns Time remaining, or null if the date has passed.
 */
function calculateTimeLeft(targetDate: Date): TimeLeft | null {
  const diff = targetDate.getTime() - Date.now();
  if (diff <= 0) return null;
  return {
    days: Math.floor(diff / (1000 * 60 * 60 * 24)),
    hours: Math.floor((diff / (1000 * 60 * 60)) % 24),
    minutes: Math.floor((diff / (1000 * 60)) % 60),
    seconds: Math.floor((diff / 1000) % 60),
  };
}

/**
 * Zero-pad a number to two digits.
 * @param n - Number to pad.
 * @returns Zero-padded string.
 */
function pad(n: number): string {
  return String(n).padStart(2, "0");
}

/**
 * Render a live countdown timer with days, hours, minutes, and seconds.
 *
 * @param props - Component props.
 * @param props.config - Block configuration from the store theme.
 * @returns A section with the countdown display and optional CTA.
 */
export function CountdownTimer({ config }: CountdownTimerProps) {
  const targetDateStr = config.target_date as string;
  const title = (config.title as string) || "Sale Ends In";
  const subtitle = (config.subtitle as string) || "";
  const ctaText = (config.cta_text as string) || "Shop the Sale";
  const ctaLink = (config.cta_link as string) || "/products";
  const bgStyle = (config.bg_style as string) || "gradient";

  const [timeLeft, setTimeLeft] = useState<TimeLeft | null>(null);
  const [expired, setExpired] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    if (!targetDateStr) return;
    const target = new Date(targetDateStr);
    if (isNaN(target.getTime())) return;

    function tick() {
      const tl = calculateTimeLeft(target);
      if (tl) {
        setTimeLeft(tl);
      } else {
        setExpired(true);
      }
    }
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [targetDateStr]);

  if (!targetDateStr || !mounted) return null;

  /** Build background styles based on config. */
  const bgClasses =
    bgStyle === "gradient"
      ? "bg-gradient-to-r from-[var(--theme-primary)] to-[var(--theme-accent)] text-[var(--theme-primary-text)]"
      : bgStyle === "solid"
        ? "bg-[var(--theme-primary)] text-[var(--theme-primary-text)]"
        : "";

  const timeUnits: { label: string; value: string }[] = timeLeft
    ? [
        { label: "Days", value: pad(timeLeft.days) },
        { label: "Hours", value: pad(timeLeft.hours) },
        { label: "Min", value: pad(timeLeft.minutes) },
        { label: "Sec", value: pad(timeLeft.seconds) },
      ]
    : [];

  return (
    <section className={`w-full py-12 sm:py-16 ${bgClasses}`}>
      <div className="mx-auto max-w-4xl px-6 text-center">
        <h2 className="font-heading text-3xl sm:text-4xl font-bold tracking-tight mb-2">
          {title}
        </h2>
        {subtitle && (
          <p className="text-lg opacity-80 mb-8">{subtitle}</p>
        )}

        {expired ? (
          <p className="text-xl font-semibold opacity-70">This event has ended</p>
        ) : (
          <>
            {/* Countdown display */}
            <div className="flex justify-center gap-3 sm:gap-6 mb-8">
              {timeUnits.map((unit) => (
                <div key={unit.label} className="flex flex-col items-center">
                  <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-xl bg-black/20 backdrop-blur-sm flex items-center justify-center">
                    <span className="font-heading text-3xl sm:text-4xl font-bold tabular-nums">
                      {unit.value}
                    </span>
                  </div>
                  <span className="text-xs sm:text-sm mt-2 opacity-70 uppercase tracking-wider">
                    {unit.label}
                  </span>
                </div>
              ))}
            </div>

            {ctaText && (
              <Link
                href={ctaLink}
                className="inline-block px-8 py-3 rounded-full bg-white/20 backdrop-blur-sm border border-white/30 font-semibold hover:bg-white/30 transition-colors"
              >
                {ctaText}
              </Link>
            )}
          </>
        )}
      </div>
    </section>
  );
}
