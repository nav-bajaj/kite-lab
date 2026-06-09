"use client";

import { SWRConfig } from "swr";
import type { Cache } from "swr";
import { ReactNode, useEffect, useMemo } from "react";
import { useAuth } from "@clerk/nextjs";
import { toast } from "sonner";
import { ApiError } from "./api-client";

interface SWRProviderProps {
  children: ReactNode;
}

// localStorage namespace for the persisted SWR cache. Bump the version
// suffix to invalidate every persisted cache after a breaking change.
const CACHE_PREFIX = "mw-swr-cache:v1:";

// Build a localStorage-backed SWR cache provider scoped to a single Clerk
// user. Persisting the cache lets a returning user see their last
// portfolio/charts instantly, then revalidate. The cache is namespaced by
// userId and purged on sign-out / user-switch (see SWRProvider) so one
// user's data can never surface for another on a shared device.
function makeLocalStorageProvider(userId: string) {
  return (): Cache => {
    const storageKey = CACHE_PREFIX + userId;

    // JSON.parse returns the SWR cache entries; the Map infers from it so
    // we don't have to restate SWR's internal State type here.
    let map;
    try {
      map = new Map(JSON.parse(localStorage.getItem(storageKey) || "[]"));
    } catch {
      map = new Map();
    }

    const persist = () => {
      try {
        localStorage.setItem(
          storageKey,
          JSON.stringify(Array.from(map.entries()))
        );
      } catch {
        // Storage unavailable or over quota — degrade to in-memory only.
      }
    };

    // beforeunload is unreliable on mobile; also flush when the tab is
    // backgrounded, which is the common "leaving" signal on phones.
    window.addEventListener("beforeunload", persist);
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") persist();
    });

    return map;
  };
}

export function SWRProvider({ children }: SWRProviderProps) {
  const { userId, isLoaded } = useAuth();

  // Purge persisted caches that don't belong to the current user. Runs on
  // sign-out (userId null → remove all) and user-switch (remove others).
  useEffect(() => {
    if (!isLoaded) return;
    try {
      const keep = userId ? CACHE_PREFIX + userId : null;
      for (let i = localStorage.length - 1; i >= 0; i--) {
        const k = localStorage.key(i);
        if (k && k.startsWith(CACHE_PREFIX) && k !== keep) {
          localStorage.removeItem(k);
        }
      }
    } catch {
      // ignore storage access errors
    }
  }, [isLoaded, userId]);

  // Only persist for a signed-in user. Signed-out sessions stay in-memory.
  const provider = useMemo(
    () => (userId ? makeLocalStorageProvider(userId) : undefined),
    [userId]
  );

  return (
    <SWRConfig
      // Remount on user change so the in-memory cache never carries across
      // identities; each user gets its own namespaced provider.
      key={userId ?? "anon"}
      value={{
        provider,
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
        // Keep showing the previous data while a new key (universe switch,
        // trade pagination) loads, instead of blanking to a skeleton.
        keepPreviousData: true,
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
