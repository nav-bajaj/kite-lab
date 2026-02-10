"use client";

import { SessionProvider } from "next-auth/react";
import { ThemeProvider } from "next-themes";
import { Toaster } from "@/components/ui/sonner";
import { UniverseProvider } from "@/contexts/universe-context";
import { SWRProvider } from "@/lib/swr-config";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <ThemeProvider
        attribute="class"
        defaultTheme="system"
        enableSystem
        disableTransitionOnChange
      >
        <SWRProvider>
          <UniverseProvider>
            {children}
          </UniverseProvider>
        </SWRProvider>
        <Toaster />
      </ThemeProvider>
    </SessionProvider>
  );
}
