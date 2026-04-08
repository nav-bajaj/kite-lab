"use client";

import { SessionProvider } from "next-auth/react";
import { ThemeProvider } from "next-themes";
import { Toaster } from "@/components/ui/sonner";
import { UniverseProvider } from "@/contexts/universe-context";
import { ApiAuthProvider } from "@/contexts/api-auth-context";
import { SWRProvider } from "@/lib/swr-config";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <ApiAuthProvider>
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
      </ApiAuthProvider>
    </SessionProvider>
  );
}
