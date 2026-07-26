"use client";

import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { useHoldings } from "@/lib/hooks";
import { formatCurrency, formatPercentValue, cn } from "@/lib/utils";
import { ArrowUpDown, TrendingUp, TrendingDown } from "lucide-react";

type SortField = "symbol" | "notional" | "pnl" | "pnl_pct" | "weight" | "holding_days";
type SortOrder = "asc" | "desc";

/** Mobile sort chips (UX study D1) — visible, first-class sorting. */
const MOBILE_SORTS: ReadonlyArray<{ field: SortField; label: string }> = [
  { field: "weight", label: "Weight" },
  { field: "pnl", label: "P&L" },
  { field: "notional", label: "Value" },
  { field: "holding_days", label: "Days" },
  { field: "symbol", label: "A–Z" },
];

export function HoldingsTable() {
  const { data, isLoading, error } = useHoldings();
  const [sortField, setSortField] = useState<SortField>("weight");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const toggleRow = (symbol: string) =>
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(symbol)) next.delete(symbol);
      else next.add(symbol);
      return next;
    });

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  if (isLoading) {
    return <HoldingsTableSkeleton />;
  }

  if (error || !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Current Holdings</CardTitle>
          <CardDescription>Failed to load holdings data</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const sortedHoldings = [...data.holdings].sort((a, b) => {
    // eslint-disable-next-line security/detect-object-injection -- sortField is a typed key of Holding (set by column-header clicks), not user input
    const aVal = a[sortField];
    // eslint-disable-next-line security/detect-object-injection -- see above
    const bVal = b[sortField];
    const modifier = sortOrder === "asc" ? 1 : -1;

    if (typeof aVal === "string" && typeof bVal === "string") {
      return aVal.localeCompare(bVal) * modifier;
    }
    return ((aVal as number) - (bVal as number)) * modifier;
  });

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Current Holdings</CardTitle>
            <CardDescription>
              {data.holdings.length} positions · {data.summary.winners} winners · {data.summary.losers} losers
            </CardDescription>
          </div>
          <Badge variant={data.summary.total_pnl >= 0 ? "default" : "destructive"}>
            {data.summary.total_pnl >= 0 ? "+" : ""}
            {formatCurrency(data.summary.total_pnl)}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {/* Mobile (UX study D1): sort chips + two-line rows + tap-to-expand */}
        <div className="md:hidden">
          <div className="flex items-center gap-2 overflow-x-auto pb-3">
            {MOBILE_SORTS.map(({ field, label }) => {
              const selected = sortField === field;
              return (
                <button
                  key={field}
                  type="button"
                  onClick={() => handleSort(field)}
                  className={cn(
                    "whitespace-nowrap rounded-full border px-3 py-1 text-xs font-semibold transition-colors",
                    selected
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border bg-card text-muted-foreground",
                  )}
                >
                  {label}
                  {selected ? (sortOrder === "desc" ? " ↓" : " ↑") : ""}
                </button>
              );
            })}
          </div>
          <div className="border-t">
            {sortedHoldings.map((holding) => {
              const isExpanded = expandedRows.has(holding.symbol);
              return (
                <button
                  key={holding.symbol}
                  type="button"
                  onClick={() => toggleRow(holding.symbol)}
                  aria-expanded={isExpanded}
                  className={cn(
                    "w-full border-b px-1 py-3 text-left transition-colors",
                    isExpanded && "bg-muted/50",
                  )}
                >
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-[15px] font-semibold">{holding.symbol}</span>
                    <PnLValue value={holding.pnl} />
                  </div>
                  <div className="mt-0.5 flex items-center justify-between gap-3">
                    <span className="text-xs text-muted-foreground tabular-nums">
                      {holding.weight.toFixed(1)}% wt · {holding.holding_days}d held
                    </span>
                    <PnLPercent value={holding.pnl_pct} />
                  </div>
                  {isExpanded && (
                    <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2 border-t border-dashed pt-3 text-[13px] tabular-nums">
                      <div>
                        <dt className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
                          Shares
                        </dt>
                        <dd>{holding.shares.toLocaleString()}</dd>
                      </div>
                      <div>
                        <dt className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
                          Avg cost
                        </dt>
                        <dd>{formatCurrency(holding.avg_cost, 2)}</dd>
                      </div>
                      <div>
                        <dt className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
                          Price
                        </dt>
                        <dd>{formatCurrency(holding.current_price, 2)}</dd>
                      </div>
                      <div>
                        <dt className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
                          Value
                        </dt>
                        <dd>{formatCurrency(holding.notional)}</dd>
                      </div>
                    </dl>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        <div className="hidden rounded-md border md:block">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[100px]">
                  <button
                    onClick={() => handleSort("symbol")}
                    className="flex items-center gap-1 hover:text-foreground"
                  >
                    Symbol
                    <ArrowUpDown className="h-3 w-3" />
                  </button>
                </TableHead>
                <TableHead className="text-right">Shares</TableHead>
                <TableHead className="text-right">Avg Cost</TableHead>
                <TableHead className="text-right">Price</TableHead>
                <TableHead className="text-right">
                  <button
                    onClick={() => handleSort("notional")}
                    className="flex items-center gap-1 ml-auto hover:text-foreground"
                  >
                    Value
                    <ArrowUpDown className="h-3 w-3" />
                  </button>
                </TableHead>
                <TableHead className="text-right">
                  <button
                    onClick={() => handleSort("pnl")}
                    className="flex items-center gap-1 ml-auto hover:text-foreground"
                  >
                    P&L (₹)
                    <ArrowUpDown className="h-3 w-3" />
                  </button>
                </TableHead>
                <TableHead className="text-right">
                  <button
                    onClick={() => handleSort("pnl_pct")}
                    className="flex items-center gap-1 ml-auto hover:text-foreground"
                  >
                    P&L (%)
                    <ArrowUpDown className="h-3 w-3" />
                  </button>
                </TableHead>
                <TableHead className="text-right">
                  <button
                    onClick={() => handleSort("weight")}
                    className="flex items-center gap-1 ml-auto hover:text-foreground"
                  >
                    Weight
                    <ArrowUpDown className="h-3 w-3" />
                  </button>
                </TableHead>
                <TableHead className="text-right">
                  <button
                    onClick={() => handleSort("holding_days")}
                    className="flex items-center gap-1 ml-auto hover:text-foreground"
                  >
                    Days
                    <ArrowUpDown className="h-3 w-3" />
                  </button>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedHoldings.map((holding) => (
                <TableRow key={holding.symbol}>
                  <TableCell className="font-medium">{holding.symbol}</TableCell>
                  <TableCell className="text-right font-mono">{holding.shares.toLocaleString()}</TableCell>
                  <TableCell className="text-right font-mono">{formatCurrency(holding.avg_cost, 2)}</TableCell>
                  <TableCell className="text-right font-mono">{formatCurrency(holding.current_price, 2)}</TableCell>
                  <TableCell className="text-right font-mono">{formatCurrency(holding.notional)}</TableCell>
                  <TableCell className="text-right">
                    <PnLValue value={holding.pnl} />
                  </TableCell>
                  <TableCell className="text-right">
                    <PnLPercent value={holding.pnl_pct} />
                  </TableCell>
                  <TableCell className="text-right font-mono">{holding.weight.toFixed(2)}%</TableCell>
                  <TableCell className="text-right text-muted-foreground">{holding.holding_days}d</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

function PnLValue({ value }: { value: number }) {
  const isPositive = value >= 0;

  return (
    <span className={cn("font-mono", isPositive ? "text-[color:var(--positive)]" : "text-[color:var(--negative)]")}>
      {isPositive ? "+" : ""}{formatCurrency(value)}
    </span>
  );
}

function PnLPercent({ value }: { value: number }) {
  const isPositive = value >= 0;

  return (
    <div className={cn("flex items-center justify-end gap-1", isPositive ? "text-[color:var(--positive)]" : "text-[color:var(--negative)]")}>
      {isPositive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
      <span className="font-mono">{formatPercentValue(value)}</span>
    </div>
  );
}

function HoldingsTableSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-4 w-60" />
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
