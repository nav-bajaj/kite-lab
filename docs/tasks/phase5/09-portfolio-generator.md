# Task 9: Portfolio Generator Component

**Status**: `pending`
**Blocked By**: #2, #14 (Job Endpoints, API Client)
**Blocks**: None

## Objective

Create a form component with dropdowns for all portfolio generation parameters.

## Tasks

- [ ] Create `portfolio-generator.tsx` in `components/admin/`
- [ ] Implement universe selector dropdown
- [ ] Implement lookback months dropdown
- [ ] Implement rebalance frequency dropdown
- [ ] Implement top-N input
- [ ] Implement vol floor input
- [ ] Implement min hold days input
- [ ] Add form validation
- [ ] Submit button creates job

## Implementation

### File: `kite-dashboard/src/components/admin/portfolio-generator.tsx`

```tsx
"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/components/ui/use-toast";
import { Loader2, Play } from "lucide-react";
import { createJob } from "@/lib/api-client";

interface PortfolioParams {
  universe: string;
  lookbackMonths: number;
  rebalanceWeeks: number;
  topN: number;
  volFloor: number;
  minHoldDays: number;
}

const defaultParams: PortfolioParams = {
  universe: "nse500",
  lookbackMonths: 6,
  rebalanceWeeks: 1,
  topN: 24,
  volFloor: 0.05,
  minHoldDays: 8,
};

const universeOptions = [
  { value: "nse500", label: "NSE 500", description: "Full mid+large cap" },
  { value: "nifty250", label: "Nifty 250", description: "Large + mid-cap" },
  { value: "nifty100", label: "Nifty 100", description: "Large-cap only" },
];

const lookbackOptions = [
  { value: 6, label: "6 months" },
  { value: 9, label: "9 months" },
  { value: 12, label: "12 months" },
];

const rebalanceOptions = [
  { value: 1, label: "Weekly" },
  { value: 2, label: "Bi-weekly" },
];

export function PortfolioGenerator() {
  const [params, setParams] = useState<PortfolioParams>(defaultParams);
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const job = await createJob({
        command: "generate_portfolio",
        universe: params.universe,
        args: {
          lookback_months: params.lookbackMonths,
          rebalance_weeks: params.rebalanceWeeks,
          top_n: params.topN,
          vol_floor: params.volFloor,
          min_hold_days: params.minHoldDays,
        },
        label: `Generate ${params.universe.toUpperCase()} Portfolio`,
      });

      toast({
        title: "Portfolio Generation Started",
        description: `Job ID: ${job.id.slice(0, 8)}`,
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to start portfolio generation",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setParams(defaultParams);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Portfolio Generator</CardTitle>
        <CardDescription>
          Configure and generate momentum portfolio signals
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Universe */}
          <div className="space-y-2">
            <Label htmlFor="universe">Universe</Label>
            <Select
              value={params.universe}
              onValueChange={(value) =>
                setParams({ ...params, universe: value })
              }
            >
              <SelectTrigger id="universe">
                <SelectValue placeholder="Select universe" />
              </SelectTrigger>
              <SelectContent>
                {universeOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    <div className="flex flex-col">
                      <span>{option.label}</span>
                      <span className="text-xs text-muted-foreground">
                        {option.description}
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Lookback Months */}
          <div className="space-y-2">
            <Label htmlFor="lookback">Lookback Period</Label>
            <Select
              value={String(params.lookbackMonths)}
              onValueChange={(value) =>
                setParams({ ...params, lookbackMonths: parseInt(value) })
              }
            >
              <SelectTrigger id="lookback">
                <SelectValue placeholder="Select lookback" />
              </SelectTrigger>
              <SelectContent>
                {lookbackOptions.map((option) => (
                  <SelectItem key={option.value} value={String(option.value)}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Rebalance Frequency */}
          <div className="space-y-2">
            <Label htmlFor="rebalance">Rebalance Frequency</Label>
            <Select
              value={String(params.rebalanceWeeks)}
              onValueChange={(value) =>
                setParams({ ...params, rebalanceWeeks: parseInt(value) })
              }
            >
              <SelectTrigger id="rebalance">
                <SelectValue placeholder="Select frequency" />
              </SelectTrigger>
              <SelectContent>
                {rebalanceOptions.map((option) => (
                  <SelectItem key={option.value} value={String(option.value)}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Top-N */}
          <div className="space-y-2">
            <Label htmlFor="topN">Top-N Holdings</Label>
            <Input
              id="topN"
              type="number"
              min={5}
              max={50}
              value={params.topN}
              onChange={(e) =>
                setParams({ ...params, topN: parseInt(e.target.value) || 24 })
              }
            />
          </div>

          {/* Vol Floor */}
          <div className="space-y-2">
            <Label htmlFor="volFloor">Vol Floor</Label>
            <Input
              id="volFloor"
              type="number"
              min={0.01}
              max={0.20}
              step={0.01}
              value={params.volFloor}
              onChange={(e) =>
                setParams({ ...params, volFloor: parseFloat(e.target.value) || 0.05 })
              }
            />
            <p className="text-xs text-muted-foreground">
              Volatility floor (0.05 = 5% daily)
            </p>
          </div>

          {/* Min Hold Days */}
          <div className="space-y-2">
            <Label htmlFor="minHoldDays">Min Hold Days</Label>
            <Input
              id="minHoldDays"
              type="number"
              min={0}
              max={30}
              value={params.minHoldDays}
              onChange={(e) =>
                setParams({ ...params, minHoldDays: parseInt(e.target.value) || 0 })
              }
            />
            <p className="text-xs text-muted-foreground">
              Minimum days to hold position (8 = one rebalance cycle)
            </p>
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-4">
            <Button type="submit" className="flex-1" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  Generate Portfolio
                </>
              )}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={handleReset}
              disabled={loading}
            >
              Reset
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
```

## Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| Universe | select | nse500 | nse500/nifty250/nifty100 | Stock universe |
| Lookback | select | 6 | 6/9/12 months | Momentum lookback period |
| Rebalance | select | 1 | 1/2 weeks | Rebalance frequency |
| Top-N | number | 24 | 5-50 | Number of holdings |
| Vol Floor | number | 0.05 | 0.01-0.20 | Volatility floor |
| Min Hold Days | number | 8 | 0-30 | Minimum hold period |

## Form Layout

```
┌─────────────────────────────────────┐
│ Portfolio Generator                 │
│ Configure and generate signals      │
├─────────────────────────────────────┤
│                                     │
│ Universe                            │
│ ┌─────────────────────────────────┐ │
│ │ NSE 500                       ▼ │ │
│ └─────────────────────────────────┘ │
│                                     │
│ Lookback Period                     │
│ ┌─────────────────────────────────┐ │
│ │ 6 months                      ▼ │ │
│ └─────────────────────────────────┘ │
│                                     │
│ Rebalance Frequency                 │
│ ┌─────────────────────────────────┐ │
│ │ Weekly                        ▼ │ │
│ └─────────────────────────────────┘ │
│                                     │
│ Top-N Holdings                      │
│ ┌─────────────────────────────────┐ │
│ │ 24                              │ │
│ └─────────────────────────────────┘ │
│                                     │
│ Vol Floor                           │
│ ┌─────────────────────────────────┐ │
│ │ 0.05                            │ │
│ └─────────────────────────────────┘ │
│ Volatility floor (0.05 = 5% daily)  │
│                                     │
│ Min Hold Days                       │
│ ┌─────────────────────────────────┐ │
│ │ 8                               │ │
│ └─────────────────────────────────┘ │
│ Minimum days to hold position       │
│                                     │
│ [▶ Generate Portfolio    ] [Reset]  │
│                                     │
└─────────────────────────────────────┘
```

## Job Arguments

When submitted, creates job with args:

```json
{
  "command": "generate_portfolio",
  "universe": "nse500",
  "args": {
    "lookback_months": 6,
    "rebalance_weeks": 1,
    "top_n": 24,
    "vol_floor": 0.05,
    "min_hold_days": 8
  },
  "label": "Generate NSE500 Portfolio"
}
```

## Validation

| Field | Validation |
|-------|------------|
| Top-N | Min 5, Max 50 |
| Vol Floor | Min 0.01, Max 0.20, Step 0.01 |
| Min Hold Days | Min 0, Max 30 |

## Verification

1. Select different universe options
2. Change parameter values
3. Click Generate - job starts
4. Loading state shows during submission
5. Toast notification on success/error
6. Reset button restores defaults

---

*Status Key: `pending` | `in_progress` | `completed`*
