"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
  useCallback,
} from "react";
import { useSupabaseAuth } from "@/contexts/supabase-auth-context";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";
import { setGlobalAuthToken, setTokenProvider } from "@/lib/api-client";

// Bridges the Supabase session token into the existing global-token slot
// that `api-client.ts` reads. supabase-js refreshes the session itself
// (autoRefreshToken) and every refresh flows through onAuthStateChange →
// SupabaseAuthProvider → the session prop here, so no polling interval is
// needed (Clerk's ~60s TTL forced a 50s poll; Supabase tokens live 1h).
//
// The global-token pattern is kept (rather than rewriting api-client.ts
// to use a React hook) because the SSE URL builders
// (getJobLogsStreamUrl / getPositionsStreamUrl) are synchronous and read
// the global directly — it MUST be eagerly repopulated on every session
// change or streams open with a stale token.

interface ApiAuthContextType {
  token: string | null;
  isLoading: boolean;
  // True once the session has loaded and we have a usable token (signed
  // in). SWR hooks gate their fetches on this so they never fire before a
  // token can be attached — which is what produced the spurious 401
  // "session expired" toast on login.
  authReady: boolean;
  error: string | null;
  refreshToken: () => Promise<void>;
}

const ApiAuthContext = createContext<ApiAuthContextType>({
  token: null,
  isLoading: true,
  authReady: false,
  error: null,
  refreshToken: async () => {},
});

export function ApiAuthProvider({ children }: { children: ReactNode }) {
  const { session, isSignedIn, isLoaded } = useSupabaseAuth();
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Session → token slots. Runs on initial resolution, sign-in, sign-out,
  // and every TOKEN_REFRESHED event (supabase-js refreshes ~5 min before
  // expiry). Deliberately does NOT flip isLoading back to true on refresh
  // — that would re-trigger loading states and flicker the UI.
  useEffect(() => {
    if (!isLoaded) return;
    const fresh = session?.access_token ?? null;
    setToken(fresh);
    setGlobalAuthToken(fresh);
    setIsLoading(false);
    setError(null);
  }, [session, isLoaded]);

  // Register an async token resolver so api-client can pull a
  // guaranteed-current token at fetch time (getSession returns the
  // refreshed session if supabase-js has rotated it since our render).
  useEffect(() => {
    if (isLoaded && isSignedIn) {
      setTokenProvider(async () => {
        const { data } = await getSupabaseBrowserClient().auth.getSession();
        return data.session?.access_token ?? null;
      });
    } else {
      setTokenProvider(null);
    }
    return () => setTokenProvider(null);
  }, [isLoaded, isSignedIn]);

  // Manual refresh escape hatch (kept for interface compatibility).
  const refreshToken = useCallback(async () => {
    if (!isLoaded || !isSignedIn) return;
    try {
      const { data, error: refreshError } =
        await getSupabaseBrowserClient().auth.refreshSession();
      if (refreshError) throw refreshError;
      const fresh = data.session?.access_token ?? null;
      setToken(fresh);
      setGlobalAuthToken(fresh);
      setError(null);
    } catch (err) {
      console.error("Failed to refresh Supabase session:", err);
      setError(err instanceof Error ? err.message : "Failed to get token");
    }
  }, [isLoaded, isSignedIn]);

  // Ready to make authed requests once the session has loaded and we have
  // a token. Authed SWR keys stay null until this is true.
  const authReady = isLoaded && isSignedIn === true && token !== null;

  return (
    <ApiAuthContext.Provider
      value={{ token, isLoading, authReady, error, refreshToken }}
    >
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
