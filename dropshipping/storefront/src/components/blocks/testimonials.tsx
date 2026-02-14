/**
 * Testimonials block -- displays customer quotes in a card grid or
 * animated slider layout for social proof.
 *
 * **For Developers:**
 *   This is a **client component** for slider animations.  Config:
 *   - ``items``  (array)  -- Testimonial objects: { quote, author, role, avatar_url }.
 *   - ``layout`` ("cards" | "slider") -- Display mode (default "cards").
 *   - ``title``  (string) -- Section heading (default "What People Are Saying").
 *
 * **For QA Engineers:**
 *   - Card layout shows a responsive grid of quote cards.
 *   - Slider layout auto-rotates with fade transition every 5 seconds.
 *   - Empty ``items`` array renders nothing.
 *   - Avatar images fall back to initials if missing.
 *
 * **For End Users:**
 *   Real customer testimonials that help you trust this store.
 *
 * @module blocks/testimonials
 */

"use client";

import { useState, useEffect } from "react";

/** A single testimonial item from the block config. */
interface TestimonialItem {
  quote: string;
  author: string;
  role?: string;
  avatar_url?: string;
}

/** Props for the {@link Testimonials} component. */
interface TestimonialsProps {
  config: Record<string, unknown>;
}

/**
 * Extract initials from a name for avatar fallback.
 * @param name - Full name string.
 * @returns 1-2 character initials.
 */
function getInitials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

/**
 * Render a testimonials section — card grid or animated slider.
 *
 * @param props - Component props.
 * @param props.config - Block configuration from the store theme.
 * @returns A section with customer testimonials.
 */
export function Testimonials({ config }: TestimonialsProps) {
  const rawItems = Array.isArray(config.items) ? config.items : [];
  const items: TestimonialItem[] = rawItems.filter(
    (item: unknown): item is TestimonialItem =>
      typeof item === "object" && item !== null && "quote" in item && "author" in item
  );
  const layout = (config.layout as string) === "slider" ? "slider" : "cards";
  const title = (config.title as string) || "What People Are Saying";

  const [activeSlide, setActiveSlide] = useState(0);

  /** Auto-rotate slider every 5 seconds. */
  useEffect(() => {
    if (layout !== "slider" || items.length <= 1) return;
    const timer = setInterval(() => {
      setActiveSlide((prev) => (prev + 1) % items.length);
    }, 5000);
    return () => clearInterval(timer);
  }, [layout, items.length]);

  if (items.length === 0) return null;

  return (
    <section className="mx-auto max-w-7xl px-6 py-16">
      <h2 className="font-heading text-3xl font-bold tracking-tight text-center mb-12">
        {title}
      </h2>

      {layout === "cards" ? (
        /* ── Card Grid ── */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {items.map((item, i) => (
            <div key={i} className="theme-card p-6 flex flex-col">
              {/* Quote mark */}
              <svg className="w-8 h-8 text-theme-primary opacity-30 mb-4 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
                <path d="M14.017 21v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151c-2.432.917-3.995 3.638-3.995 5.849h4v10H14.017zm-14.017 0v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151c-2.432.917-3.995 3.638-3.995 5.849h4v10H0z" />
              </svg>

              {/* Quote text */}
              <p className="text-base leading-relaxed mb-6 flex-1 italic opacity-90">
                &ldquo;{item.quote}&rdquo;
              </p>

              {/* Author */}
              <div className="flex items-center gap-3 pt-4 border-t border-theme-border">
                {item.avatar_url ? (
                  <img
                    src={item.avatar_url}
                    alt={item.author}
                    className="w-10 h-10 rounded-full object-cover"
                  />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-theme-primary flex items-center justify-center text-sm font-semibold text-theme-primary-text">
                    {getInitials(item.author)}
                  </div>
                )}
                <div>
                  <p className="font-semibold text-sm">{item.author}</p>
                  {item.role && (
                    <p className="text-xs text-theme-muted">{item.role}</p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* ── Slider ── */
        <div className="relative max-w-3xl mx-auto text-center">
          {items.map((item, i) => (
            <div
              key={i}
              className={`transition-all duration-500 ${
                i === activeSlide
                  ? "opacity-100 translate-y-0"
                  : "opacity-0 translate-y-4 absolute inset-0 pointer-events-none"
              }`}
            >
              <svg className="w-10 h-10 text-theme-primary opacity-30 mx-auto mb-6" viewBox="0 0 24 24" fill="currentColor">
                <path d="M14.017 21v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151c-2.432.917-3.995 3.638-3.995 5.849h4v10H14.017zm-14.017 0v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151c-2.432.917-3.995 3.638-3.995 5.849h4v10H0z" />
              </svg>

              <p className="text-xl leading-relaxed mb-8 italic opacity-90">
                &ldquo;{item.quote}&rdquo;
              </p>

              <div className="flex items-center justify-center gap-3">
                {item.avatar_url ? (
                  <img src={item.avatar_url} alt={item.author} className="w-12 h-12 rounded-full object-cover" />
                ) : (
                  <div className="w-12 h-12 rounded-full bg-theme-primary flex items-center justify-center text-sm font-bold text-theme-primary-text">
                    {getInitials(item.author)}
                  </div>
                )}
                <div className="text-left">
                  <p className="font-semibold">{item.author}</p>
                  {item.role && <p className="text-sm text-theme-muted">{item.role}</p>}
                </div>
              </div>
            </div>
          ))}

          {/* Dot navigation */}
          {items.length > 1 && (
            <div className="flex justify-center gap-2 mt-8">
              {items.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setActiveSlide(i)}
                  className={`w-2 h-2 rounded-full transition-all duration-300 ${
                    i === activeSlide
                      ? "bg-theme-primary w-6"
                      : "bg-theme-border hover:bg-theme-muted"
                  }`}
                  aria-label={`View testimonial ${i + 1}`}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
