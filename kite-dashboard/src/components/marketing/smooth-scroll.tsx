"use client";

import { useEffect } from "react";
import Lenis from "lenis";
import "lenis/dist/lenis.css";

/* design_studies trial: Lenis inertia scrolling, homepage-only (mounted from
 * page.tsx — remove the mount to revert). Lenis animates the real scroll
 * position, so the scroll-coupled pieces (grid fade, ResearchLens, nav) need
 * no changes. Skipped under prefers-reduced-motion per the study's contract;
 * touch devices keep native scrolling (Lenis default). */
export function SmoothScroll() {
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const lenis = new Lenis({ autoRaf: true });
    return () => lenis.destroy();
  }, []);
  return null;
}
