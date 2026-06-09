"use client";

import { useEffect, useState } from "react";

const DEFAULT_BREAKPOINT = 768; // Tailwind md

// True when the viewport is narrower than `breakpoint`. Used to render
// lighter/shorter charts on phones. Initialised lazily so the first client
// render already reflects the real width (charts are client-only, so there
// is no SSR/hydration mismatch to worry about).
export function useIsMobile(breakpoint: number = DEFAULT_BREAKPOINT): boolean {
  const [isMobile, setIsMobile] = useState<boolean>(() =>
    typeof window !== "undefined"
      ? window.matchMedia(`(max-width: ${breakpoint - 1}px)`).matches
      : false
  );

  useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${breakpoint - 1}px)`);
    const update = () => setIsMobile(mql.matches);
    mql.addEventListener("change", update);
    return () => mql.removeEventListener("change", update);
  }, [breakpoint]);

  return isMobile;
}
