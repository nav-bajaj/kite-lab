# Task 6: Value Cards Component

**Status**: `completed`
**Blocked By**: #2 (Portfolio Endpoints)
**Blocks**: #9

## Objective

Create the portfolio value cards component showing key metrics.

## Tasks

- [x] Create `value-cards.tsx` in `kite-dashboard/src/components/portfolio/`
- [x] Display portfolio value with holdings count
- [x] Display total return (amount and percentage)
- [x] Display CAGR
- [x] Display max drawdown
- [x] Add loading skeleton state
- [x] Add error state handling
- [x] Use `usePortfolio()` hook for data fetching

## Implementation

### File: `kite-dashboard/src/components/portfolio/value-cards.tsx`

```tsx
export function ValueCards() {
  const { data, isLoading, error } = usePortfolio();

  const stats = [
    { title: "Portfolio Value", value: formatCurrency(data.total_value), ... },
    { title: "Total Return", value: formatCurrency(data.total_return), ... },
    { title: "CAGR", value: formatPercent(data.cagr), ... },
    { title: "Max Drawdown", value: formatPercent(data.max_drawdown), ... },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat) => <Card>...</Card>)}
    </div>
  );
}
```

## Components Used

- `Card`, `CardHeader`, `CardTitle`, `CardContent` from shadcn/ui
- `Skeleton` for loading state
- `TrendingUp`, `TrendingDown`, `Wallet`, `BarChart3` icons from lucide-react

## Styling

- Green text for positive values
- Red text for negative values (max drawdown)
- Responsive grid: 1 col (mobile) → 2 cols (tablet) → 4 cols (desktop)

---

*Completed: February 12, 2026*
