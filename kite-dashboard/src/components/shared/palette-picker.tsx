"use client";

import * as React from "react";
import { useTheme } from "next-themes";
import { useUser } from "@clerk/nextjs";
import { Check, Palette } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { PALETTES, type PaletteName } from "@/lib/palettes";

/**
 * Palette picker — replaces the old light/dark toggle. Six swatches in the
 * canonical order (Mint · Ocean · Amber · Coral · Charcoal · Midnight);
 * Midnight is the dark theme. Selection applies instantly via next-themes
 * and roams across devices via Clerk unsafeMetadata (best-effort write —
 * the UI never blocks on it).
 */
export function PalettePicker() {
  const { theme, resolvedTheme, setTheme } = useTheme();
  const { user } = useUser();
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => setMounted(true), []);

  // Before mount (and for system/light/dark values) map to the effective palette.
  const active: PaletteName =
    (PALETTES.find((p) => p.name === theme)?.name as PaletteName | undefined) ??
    (resolvedTheme === "dark" ? "midnight" : "mint");

  const pick = (name: PaletteName) => {
    setTheme(name);
    // Roam the preference. unsafeMetadata is a user-writable UI preference;
    // it is validated on read (PaletteSync) and never trusted server-side.
    void user
      ?.update({ unsafeMetadata: { ...user.unsafeMetadata, palette: name } })
      .catch(() => {});
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Choose color palette">
          <Palette className="h-5 w-5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-44">
        <DropdownMenuLabel>Palette</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {PALETTES.map((p) => (
          <DropdownMenuItem
            key={p.name}
            onSelect={() => pick(p.name)}
            className="flex items-center gap-2.5"
          >
            <span
              aria-hidden
              className="h-4 w-4 shrink-0 rounded-full border"
              style={{ backgroundColor: p.swatch, borderColor: p.ring }}
            />
            <span className="flex-1">{p.label}</span>
            {mounted && active === p.name && <Check className="h-4 w-4" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
