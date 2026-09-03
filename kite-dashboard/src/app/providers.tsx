"use client";

import { ThemeProvider } from "next-themes";
import { THEME_VALUES, THEME_VALUE_MAP } from "@/lib/palettes";
import { PaletteSync } from "@/components/shared/palette-sync";
import { Toaster } from "@/components/ui/sonner";
import { UniverseProvider } from "@/contexts/universe-context";
import { ApiAuthProvider } from "@/contexts/api-auth-context";
import { SupabaseAuthProvider } from "@/contexts/supabase-auth-context";
import { SWRProvider } from "@/lib/swr-config";

// SupabaseAuthProvider owns the session subscription and MUST sit above
// every provider that reads it (ApiAuthProvider, SWRProvider,
// UniverseProvider, PaletteSync).
export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SupabaseAuthProvider>
      <ApiAuthProvider>
      {/* Palette system (DESIGN.md §2.6): next-themes stamps BOTH the class
          and data-palette attributes. Palette sheets select on
          [data-palette]; `midnight` maps to the `dark` class so the legacy
          dark variant + Midnight tokens fire together. `system` resolves
          OS-dark to Midnight and OS-light to Mint. */}
      <ThemeProvider
        attribute={["class", "data-palette"]}
        themes={THEME_VALUES}
        value={THEME_VALUE_MAP}
        defaultTheme="system"
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
    </SupabaseAuthProvider>
  );
}
