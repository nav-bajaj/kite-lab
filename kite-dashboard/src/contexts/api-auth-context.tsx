"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
  useCallback,
} from "react";
import { useAuth } from "@clerk/nextjs";
import { setGlobalAuthToken } from "@/lib/api-client";

// Bridges Clerk's session token into the existing global-token slot that
// `api-client.ts` reads. Clerk default tokens have ~60s TTL, so we
// refresh on a ~50s interval to keep the cached value fresh.
//
// The global-token pattern is kept (rather than rewriting api-client.ts
// to use a React hook) so server-side fetch callsites and any non-React
// consumers keep working unchanged.

const REFRESH_INTERVAL_MS = 50_000;

interface ApiAuthContextType {
  token: string | null;
  isLoading: boolean;
  error: string | null;
  refreshToken: () => Promise<void>;
}

const ApiAuthContext = createContext<ApiAuthContextType>({
  token: null,
  isLoading: true,
  error: null,
  refreshToken: async () => {},
});

export function ApiAuthProvider({ children }: { children: ReactNode }) {
  const { getToken, isSignedIn, isLoaded } = useAuth();
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshToken = useCallback(async () => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      setToken(null);
      setGlobalAuthToken(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const fresh = await getToken();
      setToken(fresh);
      setGlobalAuthToken(fresh);
    } catch (err) {
      console.error("Failed to fetch Clerk session token:", err);
      setError(err instanceof Error ? err.message : "Failed to get token");
      setToken(null);
      setGlobalAuthToken(null);
    } finally {
      setIsLoading(false);
    }
  }, [getToken, isLoaded, isSignedIn]);

  // Initial fetch + periodic refresh while signed in
  useEffect(() => {
    refreshToken();
    if (!isSignedIn) return;
    const id = setInterval(refreshToken, REFRESH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [refreshToken, isSignedIn]);

  return (
    <ApiAuthContext.Provider value={{ token, isLoading, error, refreshToken }}>
      {children}
    </ApiAuthContext.Provider>
  );
}

export function useApiAuth() {
  return useContext(ApiAuthContext);
}

export function useApiToken() {
  const { token } = useApiAuth();
  return token;
}
