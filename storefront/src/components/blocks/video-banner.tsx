/**
 * Video Banner block -- a responsive video embed (YouTube, Vimeo, or raw mp4)
 * with optional overlay text and call-to-action.
 *
 * **For Developers:**
 *   This is a **client component** for interaction handling.  Config:
 *   - ``video_url``  (string)  -- YouTube/Vimeo URL or direct .mp4 link.
 *   - ``poster_url`` (string)  -- Poster image shown before playback.
 *   - ``title``      (string)  -- Overlay heading text.
 *   - ``subtitle``   (string)  -- Overlay secondary text.
 *   - ``autoplay``   (boolean) -- Auto-play the video (default false, muted).
 *
 * **For QA Engineers:**
 *   - YouTube URLs are converted to embed format.
 *   - Vimeo URLs are converted to player embed format.
 *   - Direct video URLs use a native ``<video>`` element.
 *   - Autoplay requires muted attribute on ``<video>`` (browser policy).
 *   - Missing ``video_url`` renders nothing.
 *
 * **For End Users:**
 *   A video section showcasing the brand or products.
 *
 * @module blocks/video-banner
 */

"use client";

import { useState } from "react";

/** Props for the {@link VideoBanner} component. */
interface VideoBannerProps {
  config: Record<string, unknown>;
}

/**
 * Parse a YouTube URL and return the embed URL.
 * Handles youtube.com/watch?v= and youtu.be/ formats.
 *
 * @param url - The YouTube URL to parse.
 * @returns Embed URL or null if not a YouTube link.
 */
function getYouTubeEmbed(url: string): string | null {
  const match = url.match(
    /(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/
  );
  return match ? `https://www.youtube.com/embed/${match[1]}?rel=0` : null;
}

/**
 * Parse a Vimeo URL and return the embed URL.
 *
 * @param url - The Vimeo URL to parse.
 * @returns Embed URL or null if not a Vimeo link.
 */
function getVimeoEmbed(url: string): string | null {
  const match = url.match(/vimeo\.com\/(\d+)/);
  return match ? `https://player.vimeo.com/video/${match[1]}` : null;
}

/**
 * Check if a URL points to a direct video file.
 * @param url - URL to check.
 * @returns True if the URL ends with a video extension.
 */
function isDirectVideo(url: string): boolean {
  return /\.(mp4|webm|ogg)(\?.*)?$/i.test(url);
}

/**
 * Render a responsive video banner with optional overlay text.
 *
 * @param props - Component props.
 * @param props.config - Block configuration from the store theme.
 * @returns A section with the video embed and optional overlay.
 */
export function VideoBanner({ config }: VideoBannerProps) {
  const videoUrl = (config.video_url as string) || "";
  const posterUrl = (config.poster_url as string) || "";
  const title = (config.title as string) || "";
  const subtitle = (config.subtitle as string) || "";
  const autoplay = config.autoplay === true;

  const [playing, setPlaying] = useState(autoplay);

  if (!videoUrl) return null;

  const youtubeEmbed = getYouTubeEmbed(videoUrl);
  const vimeoEmbed = getVimeoEmbed(videoUrl);
  const isDirect = isDirectVideo(videoUrl);
  const hasOverlay = title || subtitle;

  return (
    <section className="relative w-full overflow-hidden bg-black">
      <div className="relative aspect-video max-h-[600px]">
        {/* YouTube embed */}
        {youtubeEmbed && (
          <iframe
            src={`${youtubeEmbed}${autoplay ? "&autoplay=1&mute=1" : ""}`}
            title={title || "Video"}
            className="absolute inset-0 w-full h-full"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        )}

        {/* Vimeo embed */}
        {vimeoEmbed && (
          <iframe
            src={`${vimeoEmbed}${autoplay ? "?autoplay=1&muted=1" : ""}`}
            title={title || "Video"}
            className="absolute inset-0 w-full h-full"
            allow="autoplay; fullscreen; picture-in-picture"
            allowFullScreen
          />
        )}

        {/* Direct video file */}
        {isDirect && (
          <>
            {!playing && posterUrl ? (
              <button
                onClick={() => setPlaying(true)}
                className="absolute inset-0 w-full h-full group"
                aria-label="Play video"
              >
                <img
                  src={posterUrl}
                  alt=""
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-black/30 flex items-center justify-center">
                  <div className="w-16 h-16 rounded-full bg-white/90 flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
                    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="var(--theme-primary)" stroke="none">
                      <polygon points="6 3 20 12 6 21 6 3" />
                    </svg>
                  </div>
                </div>
              </button>
            ) : (
              <video
                src={videoUrl}
                poster={posterUrl || undefined}
                autoPlay={autoplay || playing}
                muted={autoplay}
                controls
                playsInline
                className="absolute inset-0 w-full h-full object-cover"
              />
            )}
          </>
        )}

        {/* Fallback for non-embeddable URLs — show poster with link */}
        {!youtubeEmbed && !vimeoEmbed && !isDirect && posterUrl && (
          <img
            src={posterUrl}
            alt={title || "Video banner"}
            className="absolute inset-0 w-full h-full object-cover"
          />
        )}

        {/* Text overlay */}
        {hasOverlay && (youtubeEmbed || vimeoEmbed ? false : true) && (
          <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent flex items-end">
            <div className="p-8 sm:p-12 text-white">
              {title && (
                <h2 className="font-heading text-2xl sm:text-4xl font-bold mb-2">
                  {title}
                </h2>
              )}
              {subtitle && (
                <p className="text-lg opacity-90 max-w-xl">{subtitle}</p>
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
