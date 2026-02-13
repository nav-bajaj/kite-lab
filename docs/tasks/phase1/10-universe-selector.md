# Task 10: Implement Universe Selector and Context

**Status**: `completed`
**Blocked By**: #7 (shadcn/ui Components)
**Blocks**: #12 (Deploy)

## Objective

Create multi-universe support with a global context and selector component.

## Tasks

- [x] Create `lib/universes.ts` with universe constants
- [x] Build `lib/universe-context.tsx` React context
- [x] Create `components/shared/universe-selector.tsx` using ToggleGroup
- [x] Add universe selector to navbar
- [x] Persist selection in localStorage
- [x] Create TypeScript types

## src/lib/universes.ts

```typescript
export const UNIVERSES = {
  nse500: {
    id: "nse500",
    name: "NSE 500",
    shortName: "NSE 500",
    description: "Full mid+large cap universe",
    stocks: 499,
    riskProfile: "Growth-focused",
    expectedCagr: "~55-60%",
    expectedDrawdown: "~30%",
  },
  nifty250: {
    id: "nifty250",
    name: "Nifty 250",
    shortName: "N250",
    description: "Large + mid-cap blend",
    stocks: 250,
    riskProfile: "Balanced",
    expectedCagr: "~45-50%",
    expectedDrawdown: "~25%",
  },
  nifty100: {
    id: "nifty100",
    name: "Nifty 100",
    shortName: "N100",
    description: "Large-cap only",
    stocks: 100,
    riskProfile: "Conservative",
    expectedCagr: "~40-45%",
    expectedDrawdown: "~20%",
  },
} as const;

export type UniverseId = keyof typeof UNIVERSES;
export type Universe = (typeof UNIVERSES)[UniverseId];

export const DEFAULT_UNIVERSE: UniverseId = "nse500";

export function getUniverse(id: UniverseId): Universe {
  return UNIVERSES[id];
}

export function isValidUniverse(id: string): id is UniverseId {
  return id in UNIVERSES;
}
```

## src/lib/universe-context.tsx

```tsx
"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { UniverseId, DEFAULT_UNIVERSE, isValidUniverse, UNIVERSES } from "./universes";

interface UniverseContextType {
  universe: UniverseId;
  setUniverse: (universe: UniverseId) => void;
  universeInfo: (typeof UNIVERSES)[UniverseId];
}

const UniverseContext = createContext<UniverseContextType | undefined>(undefined);

const STORAGE_KEY = "kite-lab-universe";

export function UniverseProvider({ children }: { children: ReactNode }) {
  const [universe, setUniverseState] = useState<UniverseId>(DEFAULT_UNIVERSE);
  const [isHydrated, setIsHydrated] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && isValidUniverse(stored)) {
      setUniverseState(stored);
    }
    setIsHydrated(true);
  }, []);

  // Save to localStorage on change
  const setUniverse = (newUniverse: UniverseId) => {
    setUniverseState(newUniverse);
    localStorage.setItem(STORAGE_KEY, newUniverse);
  };

  // Prevent hydration mismatch
  if (!isHydrated) {
    return null;
  }

  return (
    <UniverseContext.Provider
      value={{
        universe,
        setUniverse,
        universeInfo: UNIVERSES[universe],
      }}
    >
      {children}
    </UniverseContext.Provider>
  );
}

export function useUniverse() {
  const context = useContext(UniverseContext);
  if (context === undefined) {
    throw new Error("useUniverse must be used within a UniverseProvider");
  }
  return context;
}
```

## src/components/shared/universe-selector.tsx

```tsx
"use client";

import { useUniverse } from "@/lib/universe-context";
import { UNIVERSES, UniverseId } from "@/lib/universes";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export function UniverseSelector() {
  const { universe, setUniverse } = useUniverse();

  return (
    <TooltipProvider>
      <ToggleGroup
        type="single"
        value={universe}
        onValueChange={(value) => {
          if (value) setUniverse(value as UniverseId);
        }}
        className="bg-muted p-1 rounded-lg"
      >
        {(Object.keys(UNIVERSES) as UniverseId[]).map((id) => {
          const info = UNIVERSES[id];
          return (
            <Tooltip key={id}>
              <TooltipTrigger asChild>
                <ToggleGroupItem
                  value={id}
                  aria-label={info.name}
                  className={cn(
                    "px-3 py-1.5 text-xs font-medium rounded-md transition-colors",
                    "data-[state=on]:bg-background data-[state=on]:shadow-sm"
                  )}
                >
                  {info.shortName}
                </ToggleGroupItem>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-xs">
                <div className="space-y-1">
                  <p className="font-medium">{info.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {info.description}
                  </p>
                  <p className="text-xs">
                    {info.stocks} stocks • {info.riskProfile}
                  </p>
                </div>
              </TooltipContent>
            </Tooltip>
          );
        })}
      </ToggleGroup>
    </TooltipProvider>
  );
}
```

## Install Tooltip Component

```bash
npx shadcn-ui@latest add tooltip
```

## Update Providers

Update `src/app/providers.tsx`:

```tsx
"use client";

import { SessionProvider } from "next-auth/react";
import { ThemeProvider } from "next-themes";
import { UniverseProvider } from "@/lib/universe-context";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <ThemeProvider
        attribute="class"
        defaultTheme="system"
        enableSystem
        disableTransitionOnChange
      >
        <UniverseProvider>{children}</UniverseProvider>
      </ThemeProvider>
    </SessionProvider>
  );
}
```

## Using Universe in Components

```tsx
"use client";

import { useUniverse } from "@/lib/universe-context";

export function PortfolioHeader() {
  const { universe, universeInfo } = useUniverse();

  return (
    <div>
      <h1 className="text-2xl font-bold">{universeInfo.name} Portfolio</h1>
      <p className="text-muted-foreground">
        {universeInfo.stocks} stocks • {universeInfo.riskProfile}
      </p>
    </div>
  );
}
```

## Using Universe in API Calls

```tsx
import { useUniverse } from "@/lib/universe-context";
import useSWR from "swr";

export function usePortfolio() {
  const { universe } = useUniverse();

  return useSWR(`/api/portfolio?universe=${universe}`, fetcher);
}
```

## Verification

1. Start dev server and sign in
2. Verify universe selector appears in navbar
3. Click different universes:
   - Toggle should highlight selected
   - Tooltip should show details on hover
4. Refresh page:
   - Selection should persist (localStorage)
5. Open DevTools → Application → Local Storage:
   - Should see `kite-lab-universe` key

## Notes

- Default universe is NSE 500
- Selection persists across sessions via localStorage
- Hydration handled to prevent SSR mismatch
- All API calls should include `?universe=` parameter
- Universe info available via `useUniverse().universeInfo`

---

*Last updated: February 2026*
