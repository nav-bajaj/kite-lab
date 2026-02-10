"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from "react";
import { UniverseId, Universe } from "@/lib/types";
import { UNIVERSES, DEFAULT_UNIVERSE, isValidUniverse } from "@/lib/universes";

const STORAGE_KEY = "kite-lab-universe";

interface UniverseContextValue {
  universeId: UniverseId;
  universe: Universe;
  setUniverse: (id: UniverseId) => void;
  isLoading: boolean;
}

const UniverseContext = createContext<UniverseContextValue | null>(null);

export function UniverseProvider({ children }: { children: ReactNode }) {
  const [universeId, setUniverseId] = useState<UniverseId>(DEFAULT_UNIVERSE);
  const [isLoading, setIsLoading] = useState(true);

  // Load saved universe from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && isValidUniverse(saved)) {
      setUniverseId(saved);
    }
    setIsLoading(false);
  }, []);

  const setUniverse = useCallback((id: UniverseId) => {
    setUniverseId(id);
    localStorage.setItem(STORAGE_KEY, id);
  }, []);

  const value: UniverseContextValue = {
    universeId,
    universe: UNIVERSES[universeId],
    setUniverse,
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
