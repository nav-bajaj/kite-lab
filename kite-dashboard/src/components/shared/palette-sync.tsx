"use client";

import * as React from "react";
import { useUser } from "@clerk/nextjs";
import { useTheme } from "next-themes";
import { isPaletteName } from "@/lib/palettes";

/**
 * One-way pull of the cross-device palette preference on session start.
 *
 * Clerk `unsafeMetadata.palette` is the roaming copy (written by the
 * palette picker on every explicit choice); next-themes/localStorage is
 * the per-device fast path that also covers signed-out marketing pages.
 * On mount, once the Clerk user resolves, the roaming value — if valid
 * and different — wins over the device value. Exactly once per page load;
 * afterwards the picker keeps both in sync at write time, so there is no
 * effect loop and no flicker on later renders.
 */
export function PaletteSync() {
  const { user, isLoaded } = useUser();
  const { theme, setTheme } = useTheme();
  const applied = React.useRef(false);

  React.useEffect(() => {
    if (!isLoaded || !user || applied.current) return;
    applied.current = true;
    const roaming = user.unsafeMetadata?.palette;
    if (isPaletteName(roaming) && roaming !== theme) {
      setTheme(roaming);
    }
  }, [isLoaded, user, theme, setTheme]);

  return null;
}
