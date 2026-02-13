# Task 8: Allocation Chart Component

**Status**: `completed`
**Blocked By**: #2 (Portfolio Endpoints)
**Blocks**: #9

## Objective

Create a pie chart showing portfolio allocation by position.

## Tasks

- [x] Create `allocation-chart.tsx` in `kite-dashboard/src/components/portfolio/`
- [x] Display pie chart with position weights
- [x] Add legend with symbol names
- [x] Add loading state
- [x] Use `useHoldings()` hook for data

## Implementation

### File: `kite-dashboard/src/components/portfolio/allocation-chart.tsx`

```tsx
import { PieChart, Pie, Cell, Legend, ResponsiveContainer, Tooltip } from "recharts";

export function AllocationChart() {
  const { data, isLoading } = useHoldings();

  const chartData = data?.holdings.map((h) => ({
    name: h.symbol,
    value: h.weight,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Allocation</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie data={chartData} dataKey="value" nameKey="name" ... />
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
```

## Color Palette

Uses a 24-color palette for distinct position colors:
- Blues, greens, oranges, purples, etc.
- Colors repeat if more than 24 positions

## Components Used

- Recharts: `PieChart`, `Pie`, `Cell`, `ResponsiveContainer`, `Tooltip`
- shadcn/ui: `Card`, `CardHeader`, `CardTitle`, `CardContent`

---

*Completed: February 12, 2026*
