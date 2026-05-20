"use client";

import { ThemeProvider } from "next-themes";
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
      <ThemeProvider
        attribute="class"
        defaultTheme="system"
        enableSystem
        disableTransitionOnChange
      >
        <SWRProvider>
          <UniverseProvider>{children}</UniverseProvider>
        </SWRProvider>
        <Toaster />
      </ThemeProvider>
    </ApiAuthProvider>
  );
}
