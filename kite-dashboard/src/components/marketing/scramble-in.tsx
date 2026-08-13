"use client";

/* design_studies loop 27 (AEYE_STUDY D3, rationed): a single decode-in
 * moment. Hand-rolled (no GSAP): when the element first enters the
 * viewport the text resolves left-to-right through a small glyph pool.
 * Reduced motion (or no IntersectionObserver) renders the final text
 * immediately. Use ONCE per page — on every heading it becomes the
 * template's personality, not ours. */

import { useEffect, useRef, useState } from "react";

const GLYPHS = "▪#=+<>[]/\\0123456789";

export function ScrambleIn({
  text,
  className = "",
  durationMs = 900,
}: {
  text: string;
  className?: string;
  durationMs?: number;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const [shown, setShown] = useState<string | null>(null);

  useEffect(() => {
    const reduce = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    let raf = 0;
    if (reduce || !("IntersectionObserver" in window) || !ref.current) {
      raf = requestAnimationFrame(() => setShown(text));
      return () => cancelAnimationFrame(raf);
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (!entries.some((e) => e.isIntersecting)) return;
        io.disconnect();
        const t0 = performance.now();
        const tick = (now: number) => {
          const p = Math.min(1, (now - t0) / durationMs);
          const settled = Math.floor(p * text.length);
          let out = text.slice(0, settled);
          for (let i = settled; i < text.length; i++) {
            const ch = text.charAt(i);
            out +=
              ch === " "
                ? " "
                : GLYPHS.charAt((i * 7 + Math.floor(now / 40)) % GLYPHS.length);
          }
          setShown(out);
          if (p < 1) raf = requestAnimationFrame(tick);
          else setShown(text);
        };
        raf = requestAnimationFrame(tick);
      },
      { threshold: 0.4 },
    );
    io.observe(ref.current);
    return () => {
      io.disconnect();
      cancelAnimationFrame(raf);
    };
  }, [text, durationMs]);

  return (
    <span ref={ref} className={className} aria-label={text}>
      {/* reserve final width from first paint; glyph frames overlay it */}
      <span aria-hidden className={shown === null ? "invisible" : "hidden"}>
        {text}
      </span>
      <span aria-hidden className={shown === null ? "hidden" : undefined}>
        {shown}
      </span>
    </span>
  );
}
