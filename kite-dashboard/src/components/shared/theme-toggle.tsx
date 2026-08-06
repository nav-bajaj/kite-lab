"use client";

import * as React from "react";
import { useTheme } from "next-themes";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { isDarkTheme } from "@/lib/palettes";

/**
 * Two-theme toggle (design_studies_clay, CLAY_STUDY.md §3) — replaces the
 * six-swatch PalettePicker on the marketing surfaces. Light is the Ocean
 * palette (the Clay-formula light theme rides its slot); dark stamps the
 * `.dark` class so the Marketworks Dark block fires. Device-local only:
 * unlike the picker this does not roam via Clerk — PaletteSync ignores
 * non-palette values by design, and the dashboard picker's fate is a
 * merge-checklist decision (STATE.md).
 */
export function ThemeToggle() {
  const { theme, resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => setMounted(true), []);

  const dark = mounted && isDarkTheme(theme, resolvedTheme);

  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
      onClick={() => setTheme(dark ? "ocean" : "dark")}
    >
      {dark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
    </Button>
  );
}
