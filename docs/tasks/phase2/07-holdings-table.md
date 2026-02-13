# Task 7: Holdings Table Component

**Status**: `completed`
**Blocked By**: #2, #3 (Portfolio Endpoints)
**Blocks**: #9

## Objective

Create a sortable table displaying all 24 holdings with P&L.

## Tasks

- [x] Create `holdings-table.tsx` in `kite-dashboard/src/components/portfolio/`
- [x] Display all holdings with columns
- [x] Add sortable columns
- [x] Color-code P&L values (green/red)
- [x] Add loading skeleton state
- [x] Use `useHoldings()` hook for data fetching

## Table Columns

| Column | Description | Sortable |
|--------|-------------|----------|
| Symbol | Stock symbol | Yes |
| Shares | Number of shares | Yes |
| Avg Cost | Entry price | Yes |
| Price | Current price | Yes |
| Value | Current notional | Yes |
| P&L | Profit/loss amount | Yes |
| P&L % | Profit/loss percentage | Yes |
| Weight | Portfolio allocation % | Yes |
| Days | Holding period | Yes |

## Implementation

### File: `kite-dashboard/src/components/portfolio/holdings-table.tsx`

```tsx
export function HoldingsTable() {
  const { data, isLoading, error } = useHoldings();
  const [sortConfig, setSortConfig] = useState({ key: "weight", dir: "desc" });

  // Sort holdings based on current config
  const sortedHoldings = useMemo(() => { ... }, [data, sortConfig]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Holdings ({data?.holdings.length || 0})</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>...</TableHeader>
          <TableBody>
            {sortedHoldings.map((h) => <TableRow>...</TableRow>)}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
```

## Styling

- P&L positive: `text-green-600 dark:text-green-400`
- P&L negative: `text-red-600 dark:text-red-400`
- Sort indicator arrows on sortable columns

---

*Completed: February 12, 2026*
