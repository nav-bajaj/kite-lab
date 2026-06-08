"use client";

import { SWRConfig } from "swr";
import { ReactNode } from "react";
import { toast } from "sonner";
import { ApiError } from "./api-client";

interface SWRProviderProps {
  children: ReactNode;
}

export function SWRProvider({ children }: SWRProviderProps) {
  return (
    <SWRConfig
      value={{
        onError: (error: Error) => {
          // Authed SWR keys are gated on auth readiness (see useAuthedSWR),
          // so a 401 here is a *genuine* failure, not the old login race.
          // Each branch uses a stable toast id so repeated failures across
          // concurrent hooks collapse into a single toast.
          if (error instanceof ApiError) {
            if (error.status === 401) {
              // Distinguish the Zerodha broker token (live prices) from the
              // Clerk login session — they fail independently.
              const isBrokerToken = /zerodha|broker|access token/i.test(
                error.message
              );
              if (isBrokerToken) {
                toast.error(
                  "Live prices paused — the Zerodha broker token needs renewing.",
                  { id: "broker-token-expired" }
                );
              } else {
                toast.error("Your session expired. Please sign in again.", {
                  id: "session-expired",
                });
              }
            } else if (error.status === 403) {
              toast.error("Access denied.", { id: "access-denied" });
            } else if (error.status >= 500) {
              toast.error("Server error. Please try again later.", {
                id: "server-error",
              });
            } else {
              toast.error(error.message);
            }
          } else {
            toast.error("Failed to fetch data.", { id: "fetch-failed" });
          }
        },
        revalidateOnFocus: true,
        revalidateOnReconnect: true,
        shouldRetryOnError: (error: Error) => {
          // Don't retry on auth errors
          if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
            return false;
          }
          return true;
        },
        errorRetryCount: 3,
        dedupingInterval: 2000,
      }}
    >
      {children}
    </SWRConfig>
  );
}
