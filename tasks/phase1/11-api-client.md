# Task 11: Create API Client with SWR Integration

**Status**: `completed`
**Blocked By**: #6 (Next.js Setup), #8 (NextAuth)
**Blocks**: #12 (Deploy)

## Objective

Set up frontend data fetching with API client and SWR hooks.

## Tasks

- [x] Create `lib/api-client.ts` with fetch wrapper
- [x] Configure base URL from environment
- [x] Add Bearer token injection from session
- [x] Add universe parameter to requests
- [x] Set up SWR provider
- [x] Create example hooks

## src/lib/api-client.ts

```typescript
import { getSession } from "next-auth/react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface FetchOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
}

class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

export async function apiFetch<T>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const { params, ...fetchOptions } = options;

  // Build URL with query params
  const url = new URL(`${API_BASE_URL}${endpoint}`);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        url.searchParams.append(key, String(value));
      }
    });
  }

  // Get session for auth token
  const session = await getSession();
  const token = (session as any)?.accessToken;

  // Build headers
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(fetchOptions.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Make request
  const response = await fetch(url.toString(), {
    ...fetchOptions,
    headers,
  });

  // Handle errors
  if (!response.ok) {
    let errorData;
    try {
      errorData = await response.json();
    } catch {
      errorData = { detail: response.statusText };
    }
    throw new ApiError(
      errorData.detail || "API request failed",
      response.status,
      errorData
    );
  }

  // Return JSON response
  return response.json();
}

// Convenience methods
export const api = {
  get: <T>(endpoint: string, params?: FetchOptions["params"]) =>
    apiFetch<T>(endpoint, { method: "GET", params }),

  post: <T>(endpoint: string, data?: any, params?: FetchOptions["params"]) =>
    apiFetch<T>(endpoint, {
      method: "POST",
      body: JSON.stringify(data),
      params,
    }),

  put: <T>(endpoint: string, data?: any) =>
    apiFetch<T>(endpoint, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  delete: <T>(endpoint: string) =>
    apiFetch<T>(endpoint, { method: "DELETE" }),
};
```

## src/lib/fetcher.ts

```typescript
import { apiFetch } from "./api-client";

// Simple fetcher for SWR
export const fetcher = <T>(url: string): Promise<T> => apiFetch<T>(url);

// Fetcher with universe parameter
export const fetcherWithUniverse = <T>(
  url: string,
  universe: string
): Promise<T> => {
  const separator = url.includes("?") ? "&" : "?";
  return apiFetch<T>(`${url}${separator}universe=${universe}`);
};
```

## src/hooks/use-portfolio.ts

```typescript
import useSWR from "swr";
import { useUniverse } from "@/lib/universe-context";
import { fetcherWithUniverse } from "@/lib/fetcher";
import type { Portfolio, Holding } from "@/lib/types";

interface PortfolioResponse {
  total_value: number;
  cash: number;
  invested: number;
  daily_pnl: number;
  daily_pnl_pct: number;
  total_return: number;
  total_return_pct: number;
  holdings_count: number;
  as_of_date: string;
}

interface HoldingsResponse {
  holdings: Holding[];
  summary: {
    total_pnl: number;
    winners: number;
    losers: number;
  };
}

export function usePortfolio() {
  const { universe } = useUniverse();

  const { data, error, isLoading, mutate } = useSWR<PortfolioResponse>(
    ["/api/portfolio", universe],
    ([url, univ]) => fetcherWithUniverse(url, univ),
    {
      refreshInterval: 5 * 60 * 1000, // 5 minutes
      revalidateOnFocus: true,
    }
  );

  return {
    portfolio: data,
    isLoading,
    isError: !!error,
    error,
    refresh: mutate,
  };
}

export function useHoldings() {
  const { universe } = useUniverse();

  const { data, error, isLoading, mutate } = useSWR<HoldingsResponse>(
    ["/api/portfolio/holdings", universe],
    ([url, univ]) => fetcherWithUniverse(url, univ),
    {
      refreshInterval: 5 * 60 * 1000,
    }
  );

  return {
    holdings: data?.holdings || [],
    summary: data?.summary,
    isLoading,
    isError: !!error,
    error,
    refresh: mutate,
  };
}
```

## src/hooks/use-metrics.ts

```typescript
import useSWR from "swr";
import { useUniverse } from "@/lib/universe-context";
import { fetcherWithUniverse } from "@/lib/fetcher";
import type { Metrics } from "@/lib/types";

export function useMetrics() {
  const { universe } = useUniverse();

  const { data, error, isLoading } = useSWR<Metrics>(
    ["/api/metrics", universe],
    ([url, univ]) => fetcherWithUniverse(url, univ),
    {
      refreshInterval: 60 * 60 * 1000, // 1 hour
    }
  );

  return {
    metrics: data,
    isLoading,
    isError: !!error,
    error,
  };
}

interface EquityCurvePoint {
  date: string;
  portfolio_value: number;
  benchmark_value: number;
  drawdown: number;
}

export function useEquityCurve(start?: string, end?: string) {
  const { universe } = useUniverse();

  const params = new URLSearchParams();
  params.set("universe", universe);
  if (start) params.set("start", start);
  if (end) params.set("end", end);

  const { data, error, isLoading } = useSWR<{ data: EquityCurvePoint[] }>(
    `/api/metrics/equity-curve?${params.toString()}`,
    fetcherWithUniverse,
    {
      refreshInterval: 60 * 60 * 1000,
    }
  );

  return {
    equityCurve: data?.data || [],
    isLoading,
    isError: !!error,
  };
}
```

## Install SWR

```bash
cd kite-dashboard
npm install swr
```

## Update Providers with SWRConfig

```tsx
// src/app/providers.tsx
"use client";

import { SessionProvider } from "next-auth/react";
import { ThemeProvider } from "next-themes";
import { UniverseProvider } from "@/lib/universe-context";
import { SWRConfig } from "swr";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <SWRConfig
        value={{
          revalidateOnFocus: true,
          revalidateOnReconnect: true,
          dedupingInterval: 10000,
          errorRetryCount: 3,
          onError: (error, key) => {
            console.error(`SWR Error [${key}]:`, error);
          },
        }}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <UniverseProvider>{children}</UniverseProvider>
        </ThemeProvider>
      </SWRConfig>
    </SessionProvider>
  );
}
```

## Example Usage in Component

```tsx
"use client";

import { usePortfolio, useHoldings } from "@/hooks/use-portfolio";
import { Skeleton } from "@/components/ui/skeleton";
import { formatCurrency } from "@/lib/utils";

export function PortfolioValue() {
  const { portfolio, isLoading, isError } = usePortfolio();

  if (isLoading) {
    return <Skeleton className="h-8 w-32" />;
  }

  if (isError) {
    return <p className="text-destructive">Failed to load portfolio</p>;
  }

  return (
    <div>
      <p className="text-3xl font-bold">
        {formatCurrency(portfolio?.total_value || 0)}
      </p>
    </div>
  );
}
```

## Environment Variables

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

For production:
```bash
NEXT_PUBLIC_API_URL=https://kite-api.railway.app
```

## Verification

1. Start both backend and frontend:
   ```bash
   # Terminal 1: Backend
   cd kite-api && uvicorn app.main:app --reload

   # Terminal 2: Frontend
   cd kite-dashboard && npm run dev
   ```

2. Open DevTools → Network tab
3. Navigate to dashboard
4. Verify API calls include:
   - Authorization header with Bearer token
   - `universe` query parameter
5. Change universe selector:
   - Should trigger new API calls with different universe

## Notes

- All API calls automatically include auth token from session
- Universe is passed via query parameter (not path)
- SWR handles caching, deduplication, and revalidation
- Error handling via ApiError class
- Hooks re-fetch when universe changes (via SWR key)

---

*Last updated: February 2026*
