"use client";

import * as React from "react";
import { useTheme } from "next-themes";
import { useSupabaseAuth } from "@/contexts/supabase-auth-context";
import { isPaletteName } from "@/lib/palettes";

/**
 * One-way pull of the cross-device palette preference on session start.
 *
 * Supabase `user_metadata.palette` is the roaming copy (written by the
 * palette picker on every explicit choice); next-themes/localStorage is
 * the per-device fast path that also covers signed-out marketing pages.
 * On mount, once the session resolves, the roaming value — if valid and
 * different — wins over the device value. Exactly once per page load;
 * afterwards the picker keeps both in sync at write time, so there is no
 * effect loop and no flicker on later renders.
 *
 * user_metadata is end-user-editable, which is fine HERE and only here:
 * a palette name is a UI preference, validated by isPaletteName on read,
 * and never trusted server-side. Roles never live in user_metadata.
 */
export function PaletteSync() {
  const { user, isLoaded } = useSupabaseAuth();
  const { theme, setTheme } = useTheme();
  const applied = React.useRef(false);

  React.useEffect(() => {
    if (!isLoaded || !user || applied.current) return;
    applied.current = true;
    const roaming = (
      user.user_metadata as { palette?: unknown } | undefined
    )?.palette;
    if (isPaletteName(roaming) && roaming !== theme) {
      setTheme(roaming);
    }
  }, [isLoaded, user, theme, setTheme]);

  return null;
}
