# Task 5: Performance Page

**Status**: `pending`
**Blocked By**: None (can start in parallel with backend)
**Blocks**: None

## Objective

Create the performance page layout and routing.

## Tasks

- [ ] Create performance page at `/performance`
- [ ] Set up page layout structure
- [ ] Add to sidebar navigation
- [ ] Import and position all components
- [ ] Add page title and universe indicator

## Implementation

### File: `kite-dashboard/src/app/(dashboard)/performance/page.tsx`

```tsx
"use client";

import {
  MetricsGrid,
  EquityCurve,
  DrawdownChart,
  MonthlyHeatmap,
  AdditionalMetrics
} from "@/components/performance";

export default function PerformancePage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Performance</h1>
        <p className="text-muted-foreground">
          Historical performance metrics and analysis
        </p>
      </div>

      {/* Primary Metrics Grid */}
      <MetricsGrid />

      {/* Equity Curve Chart */}
      <EquityCurve />

      {/* Secondary Charts Row */}
      <div className="grid gap-6 lg:grid-cols-2">
        <DrawdownChart />
        <MonthlyHeatmap />
      </div>

      {/* Additional Metrics */}
      <AdditionalMetrics />
    </div>
  );
}
```

### Update Sidebar Navigation

Add to `kite-dashboard/src/components/layout/sidebar.tsx`:

```tsx
const navItems = [
  { href: "/", label: "Portfolio", icon: Wallet },
  { href: "/performance", label: "Performance", icon: BarChart3 },
  // ... other items
];
```

## Page Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ Performance                                                      │
│ Historical performance metrics and analysis                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │   CAGR   │ │  Sharpe  │ │  Max DD  │ │ Volatility│           │
│  │  56.3%   │ │   1.87   │ │ -29.6%   │ │  25.4%   │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Equity Curve                             │ │
│  │  [Large area chart spanning full width]                     │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌───────────────────────────┐ ┌───────────────────────────────┐│
│  │ Drawdown Chart            │ │ Monthly Returns Heatmap       ││
│  └───────────────────────────┘ └───────────────────────────────┘│
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Additional Metrics (8 cards in 2x4 grid)                    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Verification

1. Navigate to `/performance` from sidebar
2. All components render without errors
3. Data loads from API correctly
4. Responsive on mobile/tablet/desktop

---

*Status Key: `pending` | `in_progress` | `completed`*
