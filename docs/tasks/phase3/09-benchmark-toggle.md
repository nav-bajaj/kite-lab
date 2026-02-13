# Task 9: Benchmark Comparison Toggle

**Status**: `pending`
**Blocked By**: #7 (Equity Curve Chart)
**Blocks**: None

## Objective

Implement benchmark comparison functionality in the equity curve chart.

## Tasks

- [ ] Add toggle button for benchmark visibility
- [ ] Overlay benchmark line on portfolio chart
- [ ] Show relative performance in tooltip
- [ ] Add legend for both lines

## Implementation

This task is integrated into the Equity Curve Chart component (Task 7).

### Toggle Controls

```tsx
<ToggleGroup type="multiple" size="sm">
  <ToggleGroupItem
    value="benchmark"
    aria-label="Toggle benchmark"
    pressed={showBenchmark}
    onPressedChange={setShowBenchmark}
  >
    Benchmark
  </ToggleGroupItem>
</ToggleGroup>
```

### Benchmark Line

```tsx
{showBenchmark && (
  <Area
    type="monotone"
    dataKey="benchmark_value"
    name="Nifty 100"
    stroke="#6b7280"
    fill="transparent"
    strokeWidth={1}
    strokeDasharray="4 4"
  />
)}
```

### Enhanced Tooltip

```tsx
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload) return null;

  const portfolio = payload.find((p: any) => p.dataKey === "portfolio_value");
  const benchmark = payload.find((p: any) => p.dataKey === "benchmark_value");

  // Calculate relative performance
  let outperformance = null;
  if (portfolio && benchmark && benchmark.value > 0) {
    const portfolioReturn = (portfolio.value / 1000000 - 1) * 100;
    const benchmarkReturn = (benchmark.value / 1000000 - 1) * 100;
    outperformance = portfolioReturn - benchmarkReturn;
  }

  return (
    <div className="rounded-lg border bg-background p-3 shadow-md">
      <p className="font-medium mb-2">{label}</p>
      {payload.map((entry: any) => (
        <p key={entry.name} style={{ color: entry.color }}>
          {entry.name}: {formatCurrency(entry.value)}
        </p>
      ))}
      {outperformance !== null && (
        <p className={outperformance >= 0 ? "text-green-600" : "text-red-600"}>
          Alpha: {outperformance >= 0 ? "+" : ""}{outperformance.toFixed(1)}%
        </p>
      )}
    </div>
  );
}
```

## Visual Design

| Element | Style |
|---------|-------|
| Portfolio | Solid blue line with fill |
| Benchmark | Dashed gray line, no fill |
| Toggle | Small button in card header |
| Legend | Shows both series names |

## Benchmark Data

The benchmark data (Nifty 100 index) is included in the equity curve response:

```json
{
  "data": [
    {
      "date": "2020-07-10",
      "portfolio_value": 1000000,
      "benchmark_value": 1000000,
      "drawdown": 0
    }
  ]
}
```

---

*Status Key: `pending` | `in_progress` | `completed`*
