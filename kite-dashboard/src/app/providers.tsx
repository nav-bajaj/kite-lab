"use client";

import { ThemeProvider } from "next-themes";
import { THEME_VALUES, THEME_VALUE_MAP } from "@/lib/palettes";
import { PaletteSync } from "@/components/shared/palette-sync";
import { Toaster } from "@/components/ui/sonner";
import { UniverseProvider } from "@/contexts/universe-context";
import { ApiAuthProvider } from "@/contexts/api-auth-context";
import { SWRProvider } from "@/lib/swr-config";

// Note: <ClerkProvider> lives in src/app/layout.tsx wrapping <html>.
// This file only carries the app-internal providers that depend on
// Clerk's session being already established.
export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ApiAuthProvider>
      {/* Palette system (DESIGN.md §2.6): next-themes stamps BOTH the class
          and data-palette attributes. Palette sheets select on
          [data-palette]; `midnight` maps to the `dark` class so the legacy
          dark variant + Midnight tokens fire together.
          design_studies loop 17: defaultTheme was "system" — Ocean is the
          study's base palette (founder call); revisit before any merge. */}
      <ThemeProvider
        attribute={["class", "data-palette"]}
        themes={THEME_VALUES}
        value={THEME_VALUE_MAP}
        defaultTheme="ocean"
        enableSystem
        disableTransitionOnChange
      >
        <PaletteSync />
        <SWRProvider>
          <UniverseProvider>{children}</UniverseProvider>
        </SWRProvider>
        <Toaster />
      </ThemeProvider>
    </ApiAuthProvider>
  );
}
