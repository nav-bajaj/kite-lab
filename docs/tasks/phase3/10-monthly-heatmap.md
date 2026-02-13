# Task 10: Monthly Returns Heatmap

**Status**: `pending`
**Blocked By**: #4 (Monthly Returns Endpoint)
**Blocks**: None

## Objective

Create a calendar-style heatmap showing monthly returns.

## Tasks

- [ ] Create `monthly-heatmap.tsx` in `kite-dashboard/src/components/performance/`
- [ ] Display returns in grid format (months x years)
- [ ] Color-code cells based on return value
- [ ] Show YTD column for each year
- [ ] Add loading state
- [ ] Create `useMonthlyReturns()` hook

## Implementation

### File: `kite-dashboard/src/components/performance/monthly-heatmap.tsx`

```tsx
"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useMonthlyReturns } from "@/lib/hooks";
import { cn } from "@/lib/utils";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function MonthlyHeatmap() {
  const { data, isLoading, error } = useMonthlyReturns();

  if (isLoading) {
    return <MonthlyHeatmapSkeleton />;
  }

  if (error || !data?.data) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">
            Failed to load monthly returns
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Monthly Returns</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="text-left p-2 font-medium">Year</th>
                {MONTHS.map((month) => (
                  <th key={month} className="p-2 font-medium text-center">
                    {month}
                  </th>
                ))}
                <th className="p-2 font-medium text-center">YTD</th>
              </tr>
            </thead>
            <tbody>
              {data.data.map((row) => (
                <tr key={row.year}>
                  <td className="p-2 font-medium">{row.year}</td>
                  {row.months.map((value, idx) => (
                    <td key={idx} className="p-1">
                      <ReturnCell value={value} />
                    </td>
                  ))}
                  <td className="p-1">
                    <ReturnCell value={row.ytd} isYtd />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

interface ReturnCellProps {
  value: number | null;
  isYtd?: boolean;
}

function ReturnCell({ value, isYtd }: ReturnCellProps) {
  if (value === null) {
    return (
      <div className="w-full h-8 rounded bg-muted/50 flex items-center justify-center">
        <span className="text-xs text-muted-foreground">—</span>
      </div>
    );
  }

  const bgColor = getColorForReturn(value);
  const textColor = Math.abs(value) > 5 ? "text-white" : "text-foreground";

  return (
    <div
      className={cn(
        "w-full h-8 rounded flex items-center justify-center",
        bgColor,
        textColor,
        isYtd && "font-semibold"
      )}
    >
      <span className="text-xs">
        {value >= 0 ? "+" : ""}{value.toFixed(1)}%
      </span>
    </div>
  );
}

function getColorForReturn(value: number): string {
  // Green gradient for positive, red gradient for negative
  if (value >= 10) return "bg-green-600";
  if (value >= 5) return "bg-green-500";
  if (value >= 2) return "bg-green-400";
  if (value >= 0) return "bg-green-200";
  if (value >= -2) return "bg-red-200";
  if (value >= -5) return "bg-red-400";
  if (value >= -10) return "bg-red-500";
  return "bg-red-600";
}

function MonthlyHeatmapSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-32" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-[200px] w-full" />
      </CardContent>
    </Card>
  );
}
```

### Add Hook: `kite-dashboard/src/lib/hooks.ts`

```tsx
export function useMonthlyReturns() {
  const { universeId } = useUniverse();

  return useSWR(
    ["monthly-returns", universeId],
    ([, universe]) => getMonthlyReturns(universe),
    {
      refreshInterval: SLOW_REFRESH,
      revalidateOnFocus: false,
    }
  );
}
```

## Color Scale

| Return Range | Color | Text |
|--------------|-------|------|
| >= +10% | green-600 | white |
| +5% to +10% | green-500 | white |
| +2% to +5% | green-400 | dark |
| 0% to +2% | green-200 | dark |
| -2% to 0% | red-200 | dark |
| -5% to -2% | red-400 | dark |
| -10% to -5% | red-500 | white |
| <= -10% | red-600 | white |

## Layout

```
┌────────────────────────────────────────────────────────────────────┐
│ Monthly Returns                                                     │
├──────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┤
│ Year │ Jan │ Feb │ Mar │ Apr │ May │ Jun │ Jul │ Aug │ Sep │ ... │
├──────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
│ 2020 │  —  │  —  │  —  │  —  │  —  │  —  │+5.2 │+8.1 │-2.3 │ ... │
│ 2021 │+7.1 │+4.6 │-1.2 │+8.9 │+3.5 │-2.1 │+5.7 │+9.0 │-0.5 │ ... │
│ 2022 │-3.5 │+2.1 │+5.7 │-8.9 │+1.2 │+4.6 │-2.3 │+6.8 │+3.2 │ ... │
│ ...  │     │     │     │     │     │     │     │     │     │     │
└──────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
```

---

*Status Key: `pending` | `in_progress` | `completed`*
