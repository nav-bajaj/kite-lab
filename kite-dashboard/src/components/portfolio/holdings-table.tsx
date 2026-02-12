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
import { formatCurrency, formatPercent, cn } from "@/lib/utils";
import { ArrowUpDown, TrendingUp, TrendingDown } from "lucide-react";

type SortField = "symbol" | "notional" | "pnl_pct" | "weight" | "holding_days";
type SortOrder = "asc" | "desc";

export function HoldingsTable() {
  const { data, isLoading, error } = useHoldings();
  const [sortField, setSortField] = useState<SortField>("weight");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

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
    const aVal = a[sortField];
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
        <div className="rounded-md border">
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
                    onClick={() => handleSort("pnl_pct")}
                    className="flex items-center gap-1 ml-auto hover:text-foreground"
                  >
                    P&L
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
                  <TableCell className="text-right">{holding.shares.toLocaleString()}</TableCell>
                  <TableCell className="text-right">{formatCurrency(holding.avg_cost)}</TableCell>
                  <TableCell className="text-right">{formatCurrency(holding.current_price)}</TableCell>
                  <TableCell className="text-right">{formatCurrency(holding.notional)}</TableCell>
                  <TableCell className="text-right">
                    <PnLCell value={holding.pnl} percent={holding.pnl_pct} />
                  </TableCell>
                  <TableCell className="text-right">{formatPercent(holding.weight)}</TableCell>
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

function PnLCell({ value, percent }: { value: number; percent: number }) {
  const isPositive = value >= 0;

  return (
    <div className={cn("flex items-center justify-end gap-1", isPositive ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400")}>
      {isPositive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
      <span>{formatPercent(percent)}</span>
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
