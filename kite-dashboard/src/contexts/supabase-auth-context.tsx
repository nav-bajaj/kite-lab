"use client";

/**
 * Session provider for Supabase Auth — the app-wide replacement for
 * Clerk's useAuth/useUser (auth_stack_v2 F2.1).
 *
 * Exposes a single subscription to onAuthStateChange; every consumer
 * (api-auth-context, SWR namespacing, universe context, nav role reads,
 * palette sync) reads from here instead of holding its own listener.
 *
 * Role note: `role` comes from the JWT's `app_metadata.role` and is for
 * COSMETIC gating only (nav visibility, universe picker filtering). The
 * backend re-verifies the token and enforces the real gates — see
 * kite-api/app/auth.py and R-022.
 */

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { Session, User } from "@supabase/supabase-js";

import { getSupabaseBrowserClient } from "@/lib/supabase/client";

interface SupabaseAuthContextValue {
  session: Session | null;
  user: User | null;
  /** True once the initial session has been resolved (even if absent). */
  isLoaded: boolean;
  isSignedIn: boolean;
  /** Supabase user UUID, null when signed out. */
  userId: string | null;
  /** "admin" | "client" — from app_metadata.role, cosmetic use only. */
  role: "admin" | "client";
  signOut: () => Promise<void>;
}

const SupabaseAuthContext = createContext<SupabaseAuthContextValue | null>(
  null,
);

export function SupabaseAuthProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [session, setSession] = useState<Session | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    const supabase = getSupabaseBrowserClient();

    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setIsLoaded(true);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next);
      setIsLoaded(true);
    });

    return () => subscription.unsubscribe();
  }, []);

  const value = useMemo<SupabaseAuthContextValue>(() => {
    const user = session?.user ?? null;
    const metaRole = (
      user?.app_metadata as { role?: string } | undefined
    )?.role;
    return {
      session,
      user,
      isLoaded,
      isSignedIn: session !== null,
      userId: user?.id ?? null,
      role: metaRole === "admin" ? "admin" : "client",
      signOut: async () => {
        await getSupabaseBrowserClient().auth.signOut();
        // Middleware bounces unauthenticated visitors off protected
        // routes; send them to the marketing page explicitly so the
        // redirect is deterministic.
        window.location.assign("/");
      },
    };
  }, [session, isLoaded]);

  return (
    <SupabaseAuthContext.Provider value={value}>
      {children}
    </SupabaseAuthContext.Provider>
  );
}

export function useSupabaseAuth(): SupabaseAuthContextValue {
  const ctx = useContext(SupabaseAuthContext);
  if (!ctx) {
    throw new Error(
      "useSupabaseAuth must be used within SupabaseAuthProvider",
    );
  }
  return ctx;
}
