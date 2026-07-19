"use client";

import { useEffect, useRef } from "react";

import { cn } from "@/lib/utils";

/**
 * Scroll-reactive dot field for the marketing base (homepage_visual_refresh).
 *
 * Fixed to the viewport with a centre-weighted radial mask, so the in-focus
 * part of the screen always carries the pattern as you scroll, fading toward
 * the top/bottom edges — the pattern "follows" the section in focus. The dots
 * also gently breathe (grow a little, then shrink) as you scroll, tied to
 * scroll position. Purely decorative; under prefers-reduced-motion it renders
 * static (no breathing). Sits at z-0 behind the page content.
 */
export function FlowDots({ className }: { className?: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let raf = 0;
    let size = 22;
    let active = true;

    const tick = () => {
      if (!active) return;
      const sc = window.scrollY || 0;
      // gentle breathing: dot pitch eases toward a scroll-driven sine (17–27px)
      const target = 22 + Math.sin(sc / 700) * 5;
      size += (target - size) * 0.06;
      const px = size.toFixed(2);
      el.style.backgroundSize = `${px}px ${px}px`;
      raf = requestAnimationFrame(tick);
    };

    const onVisibility = () => {
      active = !document.hidden;
      if (active) raf = requestAnimationFrame(tick);
    };
    document.addEventListener("visibilitychange", onVisibility);
    raf = requestAnimationFrame(tick);

    return () => {
      active = false;
      cancelAnimationFrame(raf);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  return (
    <div
      ref={ref}
      aria-hidden
      className={cn(
        "mw-dots pointer-events-none fixed inset-0 z-0 [mask-image:radial-gradient(75%_52%_at_50%_47%,#000_22%,transparent_82%)]",
        className,
      )}
    />
  );
}
