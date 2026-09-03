"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  ReactNode,
} from "react";
import { useSupabaseAuth } from "@/contexts/supabase-auth-context";
import { UniverseId, Universe } from "@/lib/types";
import {
  UNIVERSES,
  DEFAULT_UNIVERSE,
  isValidUniverse,
  getVisibleUniverseIds,
} from "@/lib/universes";

const STORAGE_KEY = "marketworks-universe";
// One-shot migration: existing users had their selection stored under
// "kite-lab-universe" before the Marketworks rebrand. On first mount we
// read the old key, copy it to the new one, and remove the old.
const LEGACY_STORAGE_KEY = "kite-lab-universe";

interface UniverseContextValue {
  universeId: UniverseId;
  universe: Universe;
  setUniverse: (id: UniverseId) => void;
  /** Universes the current user can pick — admins see all 7, clients
   *  see only the 4 production products. */
  visibleUniverseIds: UniverseId[];
  isLoading: boolean;
}

const UniverseContext = createContext<UniverseContextValue | null>(null);

export function UniverseProvider({ children }: { children: ReactNode }) {
  // Role from the Supabase JWT's app_metadata (cosmetic filter only —
  // the backend enforces the real universe gate, R-022). Admins see all
  // 7 universes; everyone else gets the 4-product client surface.
  const { role, isLoaded } = useSupabaseAuth();
  const [universeId, setUniverseId] = useState<UniverseId>(DEFAULT_UNIVERSE);
  const [isLoading, setIsLoading] = useState(true);

  const visibleUniverseIds = useMemo(
    () => getVisibleUniverseIds(role),
    [role],
  );

  // Load saved universe from localStorage on mount (with legacy-key migration).
  // setState inside useEffect is intentional: localStorage is unavailable during
  // SSR, so we hydrate after mount. The flash-of-default is acceptable.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    let saved = localStorage.getItem(STORAGE_KEY);
    if (!saved) {
      const legacy = localStorage.getItem(LEGACY_STORAGE_KEY);
      if (legacy && isValidUniverse(legacy)) {
        localStorage.setItem(STORAGE_KEY, legacy);
        saved = legacy;
      }
      if (legacy !== null) {
        localStorage.removeItem(LEGACY_STORAGE_KEY);
      }
    }
    if (saved && isValidUniverse(saved)) {
      setUniverseId(saved);
    }
    setIsLoading(false);
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  // If the role changes (e.g. an admin signs in / out) and the currently
  // selected universe is no longer visible to them, fall back to the
  // default. Runs once Clerk's user state is loaded so we don't bounce on
  // first paint before role is known.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (!isLoaded) return;
    if (!visibleUniverseIds.includes(universeId)) {
      setUniverseId(DEFAULT_UNIVERSE);
      localStorage.setItem(STORAGE_KEY, DEFAULT_UNIVERSE);
    }
  }, [isLoaded, visibleUniverseIds, universeId]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const setUniverse = useCallback((id: UniverseId) => {
    setUniverseId(id);
    localStorage.setItem(STORAGE_KEY, id);
  }, []);

  const value: UniverseContextValue = {
    universeId,
    // eslint-disable-next-line security/detect-object-injection -- universeId is a typed UniverseId literal, UNIVERSES is a closed Record
    universe: UNIVERSES[universeId],
    setUniverse,
    visibleUniverseIds,
    isLoading,
  };

  return (
    <UniverseContext.Provider value={value}>
      {children}
    </UniverseContext.Provider>
  );
}

export function useUniverse() {
  const context = useContext(UniverseContext);
  if (!context) {
    throw new Error("useUniverse must be used within a UniverseProvider");
  }
  return context;
}
