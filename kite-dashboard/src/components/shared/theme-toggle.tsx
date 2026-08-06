"use client";

import * as React from "react";
import { useTheme } from "next-themes";
import { useUser } from "@clerk/nextjs";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * Light/dark toggle (design_studies loop 3) — replaces the six-swatch
 * PalettePicker on marketing surfaces per the two-theme endgame. Light maps
 * to `mint`, dark to `midnight` (the palette system's canonical pair), so
 * PaletteSync and Clerk roaming keep working unchanged; the Horizon study
 * scope restyles both on the surfaces that carry it.
 */
export function ThemeToggle() {
  const { theme, resolvedTheme, setTheme } = useTheme();
  const { user } = useUser();
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => setMounted(true), []);

  const isDark = mounted && (theme === "midnight" || resolvedTheme === "dark");

  const toggle = () => {
    const next = isDark ? "mint" : "midnight";
    setTheme(next);
    void user
      ?.update({ unsafeMetadata: { ...user.unsafeMetadata, palette: next } })
      .catch(() => {});
  };

  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
      onClick={toggle}
    >
      {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
    </Button>
  );
}
