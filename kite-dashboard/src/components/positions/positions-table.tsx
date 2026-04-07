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
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowUpDown, TrendingUp, TrendingDown } from "lucide-react";
import { formatCurrency, formatPercentValue, getPnLClass } from "@/lib/utils";
import type { Position } from "@/lib/types";

interface PositionsTableProps {
  positions: Position[];
  isLoading: boolean;
}

type SortField = keyof Position;
type SortOrder = "asc" | "desc";

export function PositionsTable({ positions, isLoading }: PositionsTableProps) {
  const [sortField, setSortField] = useState<SortField>("total_pnl");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  if (isLoading) {
    return <PositionsTableSkeleton />;
  }

  if (!positions || positions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Open Positions</CardTitle>
          <CardDescription>No positions found</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Sync your holdings to see live positions.
          </p>
        </CardContent>
      </Card>
    );
  }

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  const sortedPositions = [...positions].sort((a, b) => {
    const modifier = sortOrder === "asc" ? 1 : -1;
    const aVal = a[sortField];
    const bVal = b[sortField];

    if (typeof aVal === "string" && typeof bVal === "string") {
      return aVal.localeCompare(bVal) * modifier;
    }
    return ((aVal as number) - (bVal as number)) * modifier;
  });

  // Calculate totals
  const totals = positions.reduce(
    (acc, pos) => ({
      invested: acc.invested + pos.invested,
      current_value: acc.current_value + pos.current_value,
      total_pnl: acc.total_pnl + pos.total_pnl,
      day_pnl: acc.day_pnl + pos.day_pnl,
    }),
    { invested: 0, current_value: 0, total_pnl: 0, day_pnl: 0 }
  );

  const totalPnlPct = (totals.total_pnl / totals.invested) * 100;
  const dayPnlPct = (totals.day_pnl / totals.invested) * 100;

  const SortableHeader = ({
    field,
    children,
    className = "",
  }: {
    field: SortField;
    children: React.ReactNode;
    className?: string;
  }) => (
    <TableHead className={className}>
      <button
        onClick={() => handleSort(field)}
        className="flex items-center gap-1 hover:text-foreground transition-colors"
      >
        {children}
        <ArrowUpDown className="h-3 w-3" />
      </button>
    </TableHead>
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Open Positions</CardTitle>
        <CardDescription>
          {positions.length} positions • Day change is relative to previous close
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <SortableHeader field="symbol">Symbol</SortableHeader>
                <SortableHeader field="qty" className="text-right">
                  Qty
                </SortableHeader>
                <SortableHeader field="avg_price" className="text-right">
                  Entry
                </SortableHeader>
                <SortableHeader field="ltp" className="text-right">
                  LTP
                </SortableHeader>
                <SortableHeader field="invested" className="text-right">
                  Invested
                </SortableHeader>
                <SortableHeader field="current_value" className="text-right">
                  Current
                </SortableHeader>
                <SortableHeader field="total_pnl" className="text-right">
                  Total P&L
                </SortableHeader>
                <SortableHeader field="total_pnl_pct" className="text-right">
                  Total %
                </SortableHeader>
                <SortableHeader field="day_pnl" className="text-right">
                  Day P&L
                </SortableHeader>
                <SortableHeader field="day_pnl_pct" className="text-right">
                  Day %
                </SortableHeader>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedPositions.map((position) => (
                <TableRow key={position.symbol}>
                  <TableCell className="font-medium">
                    <div className="flex items-center gap-2">
                      {position.total_pnl >= 0 ? (
                        <TrendingUp className="h-4 w-4 text-green-500" />
                      ) : (
                        <TrendingDown className="h-4 w-4 text-red-500" />
                      )}
                      {position.symbol}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">{position.qty}</TableCell>
                  <TableCell className="text-right">
                    {formatCurrency(position.avg_price)}
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {formatCurrency(position.ltp)}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatCurrency(position.invested)}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatCurrency(position.current_value)}
                  </TableCell>
                  <TableCell
                    className={`text-right font-medium ${getPnLClass(
                      position.total_pnl
                    )}`}
                  >
                    {formatCurrency(position.total_pnl)}
                  </TableCell>
                  <TableCell
                    className={`text-right ${getPnLClass(position.total_pnl_pct)}`}
                  >
                    {formatPercentValue(position.total_pnl_pct)}
                  </TableCell>
                  <TableCell
                    className={`text-right font-medium ${getPnLClass(
                      position.day_pnl
                    )}`}
                  >
                    {formatCurrency(position.day_pnl)}
                  </TableCell>
                  <TableCell
                    className={`text-right ${getPnLClass(position.day_pnl_pct)}`}
                  >
                    {formatPercentValue(position.day_pnl_pct)}
                  </TableCell>
                </TableRow>
              ))}

              {/* Totals Row */}
              <TableRow className="border-t-2 bg-muted/50 font-bold">
                <TableCell>TOTAL</TableCell>
                <TableCell className="text-right">-</TableCell>
                <TableCell className="text-right">-</TableCell>
                <TableCell className="text-right">-</TableCell>
                <TableCell className="text-right">
                  {formatCurrency(totals.invested)}
                </TableCell>
                <TableCell className="text-right">
                  {formatCurrency(totals.current_value)}
                </TableCell>
                <TableCell
                  className={`text-right ${getPnLClass(totals.total_pnl)}`}
                >
                  {formatCurrency(totals.total_pnl)}
                </TableCell>
                <TableCell className={`text-right ${getPnLClass(totalPnlPct)}`}>
                  {formatPercentValue(totalPnlPct)}
                </TableCell>
                <TableCell
                  className={`text-right ${getPnLClass(totals.day_pnl)}`}
                >
                  {formatCurrency(totals.day_pnl)}
                </TableCell>
                <TableCell className={`text-right ${getPnLClass(dayPnlPct)}`}>
                  {formatPercentValue(dayPnlPct)}
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

function PositionsTableSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-4 w-60" />
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
