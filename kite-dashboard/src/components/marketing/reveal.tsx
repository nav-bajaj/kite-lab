"use client";

import { useLayoutEffect, useRef, type ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * Scroll/load reveal that ENHANCES an already-visible default (DESIGN.md §6).
 *
 * The critical correctness rule (a bug caught in the mock): visibility is never
 * gated on JavaScript. Server render and no-JS render the content visible; the
 * hidden pre-animation state is applied only client-side, in useLayoutEffect
 * (before first paint, so no flash) via the `data-reveal` attribute — driven
 * directly on the node, not through React state, so there is no cascading
 * re-render. Elements already in view reveal on the next frame; below-fold
 * elements reveal on intersect, with a safety timeout so a failed observer can
 * never leave a blank section. Under prefers-reduced-motion the content stays
 * in its visible default and never hides.
 */
export function Reveal({
  children,
  className,
  delayMs = 0,
}: {
  children: ReactNode;
  className?: string;
  delayMs?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce || !("IntersectionObserver" in window)) return; // stays visible

    // Prepare the hidden state before first paint (useLayoutEffect → no flash).
    el.dataset.reveal = "hidden";
    const show = () => {
      el.dataset.reveal = "shown";
    };

    const rect = el.getBoundingClientRect();
    const inView = rect.top < window.innerHeight * 0.9 && rect.bottom > 0;
    if (inView) {
      const raf = requestAnimationFrame(show);
      return () => cancelAnimationFrame(raf);
    }

    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            show();
            io.disconnect();
          }
        }
      },
      { threshold: 0.16 },
    );
    io.observe(el);
    const safety = setTimeout(show, 3000);
    return () => {
      io.disconnect();
      clearTimeout(safety);
    };
  }, []);

  return (
    <div
      ref={ref}
      style={delayMs ? { transitionDelay: `${delayMs}ms` } : undefined}
      className={cn("mw-reveal", className)}
    >
      {children}
    </div>
  );
}
