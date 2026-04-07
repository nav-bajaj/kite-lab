"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
  useCallback,
} from "react";
import { useSession } from "next-auth/react";
import { setGlobalAuthToken } from "@/lib/api-client";

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
  const { data: session, status } = useSession();
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshToken = useCallback(async () => {
    if (status !== "authenticated" || !session?.user?.email) {
      setToken(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/backend-token");

      if (!response.ok) {
        const data = await response.json().catch(() => ({ error: "Unknown error" }));
        throw new Error(data.error || "Failed to get token");
      }

      const data = await response.json();
      setToken(data.access_token);
      setGlobalAuthToken(data.access_token);
    } catch (err) {
      console.error("Failed to get backend token:", err);
      setError(err instanceof Error ? err.message : "Failed to get token");
      setToken(null);
      setGlobalAuthToken(null);
    } finally {
      setIsLoading(false);
    }
  }, [session, status]);

  // Sync token to global state whenever it changes
  useEffect(() => {
    setGlobalAuthToken(token);
  }, [token]);

  // Get token when session changes
  useEffect(() => {
    if (status === "loading") {
      return;
    }

    refreshToken();
  }, [status, refreshToken]);

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
