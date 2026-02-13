# Phase 3: Performance Metrics

**Duration**: Week 5-6
**Status**: Not Started
**Target Start**: February 13, 2026

## Objectives

- Display historical equity curve for each universe
- Show comprehensive performance metrics dashboard
- Benchmark comparison with Nifty 100 index
- Drawdown visualization
- Monthly returns heatmap
- Seamless universe switching with different performance data

## Production URLs

| Service | URL |
|---------|-----|
| Frontend | https://kite-lab.vercel.app |
| Backend | https://kite-lab-production.up.railway.app |

## Task Progress

### Backend Tasks

| # | Task | Status | Description |
|---|------|--------|-------------|
| 1 | Metrics service | `pending` | Calculate metrics from equity curve data |
| 2 | Metrics endpoint | `pending` | GET /api/metrics?universe=nse500 |
| 3 | Equity curve endpoint | `pending` | GET /api/metrics/equity-curve |
| 4 | Monthly returns endpoint | `pending` | GET /api/metrics/monthly-returns |

### Frontend Tasks

| # | Task | Status | Description |
|---|------|--------|-------------|
| 5 | Performance page | `pending` | Page layout and routing |
| 6 | Metrics grid | `pending` | Key metrics cards (CAGR, Sharpe, etc.) |
| 7 | Equity curve chart | `pending` | Interactive line chart with Recharts |
| 8 | Drawdown chart | `pending` | Drawdown visualization |
| 9 | Benchmark toggle | `pending` | Overlay benchmark comparison |
| 10 | Monthly heatmap | `pending` | Monthly returns calendar view |

## Dependency Graph

```
Backend:                              Frontend:
┌───┐                                ┌───┐
│ 1 │ Metrics Service                │ 5 │ Performance Page
└─┬─┘                                └─┬─┘
  │                                    │
  ├────────┬────────┐                  ├────────┬────────┬────────┐
  ▼        ▼        ▼                  ▼        ▼        ▼        ▼
┌───┐    ┌───┐    ┌───┐              ┌───┐    ┌───┐    ┌───┐    ┌────┐
│ 2 │    │ 3 │    │ 4 │              │ 6 │    │ 7 │    │ 8 │    │ 10 │
└───┘    └───┘    └───┘              └─┬─┘    └─┬─┘    └───┘    └────┘
Metrics  Equity   Monthly             │        │       Drawdown  Heatmap
         Curve    Returns             │        │
                                      │        ▼
                                      │      ┌───┐
                                      └─────▶│ 9 │
                                             └───┘
                                            Benchmark
```

## Deliverables Checklist

- [ ] Performance page accessible at `/performance`
- [ ] Equity curve from 2020 to present for each universe
- [ ] All key metrics displayed (CAGR, Sharpe, Max DD, Volatility)
- [ ] Benchmark comparison with Nifty 100
- [ ] Drawdown chart visualization
- [ ] Monthly returns heatmap
- [ ] Different metrics visible when switching universes

## Data Sources

### Database Tables Used

| Table | Columns Used |
|-------|--------------|
| `equity_curve` | `date`, `portfolio_value`, `benchmark`, `drawdown` |
| `metrics` | All performance metrics |

### Expected Metrics

| Metric | Description | Source |
|--------|-------------|--------|
| CAGR | Compound annual growth rate | metrics table |
| Total Return | Cumulative return | metrics table |
| Max Drawdown | Largest peak-to-trough decline | metrics table |
| Sharpe Ratio | Risk-adjusted return | Calculated |
| Sortino Ratio | Downside risk-adjusted return | Calculated |
| Volatility | Annualized standard deviation | Calculated |
| Calmar Ratio | CAGR / Max Drawdown | Calculated |
| Avg Turnover | Average weekly turnover | metrics table |
| Hit Rate | Winning trades percentage | metrics table |
| Avg Holding Days | Average position duration | metrics table |

## API Endpoints

### GET /api/metrics

Returns comprehensive performance metrics.

**Query Parameters:**
- `universe`: `nse500` | `nifty100` | `nifty250`

**Response:**
```json
{
  "period": {
    "start": "2020-07-10",
    "end": "2026-02-13",
    "days": 2042
  },
  "returns": {
    "total_return": 1116.25,
    "cagr": 56.36,
    "mtd": 2.34,
    "ytd": 8.45
  },
  "risk": {
    "max_drawdown": -29.60,
    "max_dd_duration": 87,
    "volatility": 25.4,
    "sharpe_ratio": 1.87,
    "sortino_ratio": 2.45,
    "calmar_ratio": 1.90
  },
  "activity": {
    "total_trades": 2352,
    "avg_turnover": 2.5,
    "annualized_turnover": 123.0,
    "avg_holding_days": 43.3,
    "hit_rate": 49.3
  }
}
```

### GET /api/metrics/equity-curve

Returns daily equity curve data for charting.

**Query Parameters:**
- `universe`: `nse500` | `nifty100` | `nifty250`
- `start`: ISO date (optional)
- `end`: ISO date (optional)

**Response:**
```json
{
  "data": [
    {
      "date": "2020-07-10",
      "portfolio_value": 1000000,
      "benchmark_value": 1000000,
      "drawdown": 0
    },
    ...
  ]
}
```

### GET /api/metrics/monthly-returns

Returns monthly returns matrix for heatmap.

**Response:**
```json
{
  "years": [2020, 2021, 2022, 2023, 2024, 2025, 2026],
  "data": [
    { "year": 2020, "months": [null, null, null, null, null, null, 5.2, 8.1, -2.3, 12.4, 6.7, 3.2], "ytd": 38.5 },
    ...
  ]
}
```

## UI Components

### Performance Page Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ Performance                            [Universe: NSE 500 ▼]    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │   CAGR   │ │  Sharpe  │ │  Max DD  │ │ Volatility│           │
│  │  56.3%   │ │   1.87   │ │ -29.6%   │ │  25.4%   │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Equity Curve                             │ │
│  │  [Area Chart: Portfolio vs Benchmark, 2020-2026]           │ │
│  │                                                             │ │
│  │  14M ─┤                                            ╭───     │ │
│  │  12M ─┤                                        ╭───╯        │ │
│  │  10M ─┤                                    ╭───╯            │ │
│  │   8M ─┤                               ╭────╯                │ │
│  │   6M ─┤                          ╭────╯                     │ │
│  │   4M ─┤                    ╭─────╯                          │ │
│  │   2M ─┤           ╭────────╯                                │ │
│  │   1M ─┼───────────╯                                         │ │
│  │       └──────┬──────┬──────┬──────┬──────┬──────┬───────   │ │
│  │           2020   2021   2022   2023   2024   2025   2026    │ │
│  │                                                             │ │
│  │  [Toggle: Portfolio ● | Benchmark ○ | Drawdown ○]          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌───────────────────────────┐ ┌───────────────────────────────┐│
│  │ Drawdown Chart            │ │ Monthly Returns Heatmap       ││
│  │ [Area chart below zero]   │ │ [Calendar grid with colors]   ││
│  └───────────────────────────┘ └───────────────────────────────┘│
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Additional Metrics                                          │ │
│  │ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐│ │
│  │ │ Sortino    │ │ Calmar     │ │ Hit Rate   │ │ Avg Hold   ││ │
│  │ │   2.45     │ │   1.90     │ │  49.3%     │ │  43.3 days ││ │
│  │ └────────────┘ └────────────┘ └────────────┘ └────────────┘│ │
│  │ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐│ │
│  │ │ Turnover   │ │ Total Trds │ │ Start Date │ │ End Date   ││ │
│  │ │  123% ann  │ │   2,352    │ │ 2020-07-10 │ │ 2026-02-13 ││ │
│  │ └────────────┘ └────────────┘ └────────────┘ └────────────┘│ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Technical Notes

### Equity Curve Data Volume

- ~1400 data points per universe (daily from Jul 2020)
- Frontend should handle large datasets efficiently
- Consider data downsampling for initial load

### Chart Library

Using Recharts for consistency with Phase 2:
- `AreaChart` for equity curve
- `LineChart` for benchmark overlay
- Custom tooltip with formatted values

### Color Scheme

| Element | Light Mode | Dark Mode |
|---------|------------|-----------|
| Portfolio line | Blue (#3b82f6) | Blue (#60a5fa) |
| Benchmark line | Gray (#6b7280) | Gray (#9ca3af) |
| Positive return | Green (#16a34a) | Green (#22c55e) |
| Negative return | Red (#dc2626) | Red (#ef4444) |
| Drawdown fill | Red with 20% opacity | Red with 20% opacity |

## Files to Create

### Backend
- `kite-api/app/services/metrics_service.py`
- `kite-api/app/api/metrics.py`

### Frontend
- `kite-dashboard/src/app/(dashboard)/performance/page.tsx`
- `kite-dashboard/src/components/performance/metrics-grid.tsx`
- `kite-dashboard/src/components/performance/equity-curve.tsx`
- `kite-dashboard/src/components/performance/drawdown-chart.tsx`
- `kite-dashboard/src/components/performance/benchmark-toggle.tsx`
- `kite-dashboard/src/components/performance/monthly-heatmap.tsx`
- `kite-dashboard/src/components/performance/index.ts`
- `kite-dashboard/src/lib/hooks.ts` (add useMetrics, useEquityCurve)

---

*Status Key: `pending` | `in_progress` | `completed`*

*Last updated: February 13, 2026*
