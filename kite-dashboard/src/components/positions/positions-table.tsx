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

/** Mobile sort chips (UX study D1) — sorting is first-class on a ranked
 *  product, so it stays visible instead of hiding behind an icon. */
const MOBILE_SORTS: ReadonlyArray<{ field: SortField; label: string }> = [
  { field: "total_pnl", label: "P&L" },
  { field: "day_pnl", label: "Day" },
  { field: "current_value", label: "Value" },
  { field: "symbol", label: "A–Z" },
];

/** Mobile position row — two lines + tap-to-expand (UX study D1).
 *  Line 1: symbol + total P&L (the question the page answers).
 *  Line 2: qty · avg + return chip. Detail lives behind the tap. */
function MobilePositionRow({
  position,
  isExpanded,
  onToggle,
}: {
  position: Position;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-expanded={isExpanded}
      className={`w-full border-b px-1 py-3 text-left transition-colors ${
        isExpanded ? "bg-muted/50" : ""
      }`}
    >
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-[15px] font-semibold">{position.symbol}</span>
        <span
          className={`text-[15px] font-semibold tabular-nums ${getPnLClass(position.total_pnl)}`}
        >
          {position.total_pnl >= 0 ? "+" : ""}
          {formatCurrency(position.total_pnl)}
        </span>
      </div>
      <div className="mt-0.5 flex items-center justify-between gap-3">
        <span className={`text-xs tabular-nums ${getPnLClass(position.day_pnl)}`}>
          {position.day_pnl >= 0 ? "+" : ""}
          {formatCurrency(position.day_pnl)} ({formatPercentValue(position.day_pnl_pct)}) today
        </span>
        <span
          className={`rounded-full px-2 py-px text-xs font-semibold tabular-nums ${getPnLClass(
            position.total_pnl_pct,
          )} ${position.total_pnl_pct >= 0 ? "bg-green-600/10" : "bg-red-600/10"}`}
        >
          {formatPercentValue(position.total_pnl_pct)}
        </span>
      </div>
      {isExpanded && (
        <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2 border-t border-dashed pt-3 text-[13px] tabular-nums">
          <div>
            <dt className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
              Qty
            </dt>
            <dd>{position.qty}</dd>
          </div>
          <div>
            <dt className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
              Avg price
            </dt>
            <dd>{formatCurrency(position.avg_price)}</dd>
          </div>
          <div>
            <dt className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
              LTP
            </dt>
            <dd>{formatCurrency(position.ltp)}</dd>
          </div>
          <div>
            <dt className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
              Invested
            </dt>
            <dd>{formatCurrency(position.invested)}</dd>
          </div>
          <div>
            <dt className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
              Current
            </dt>
            <dd>{formatCurrency(position.current_value)}</dd>
          </div>
        </dl>
      )}
    </button>
  );
}

// Defined at module scope to satisfy react-hooks/static-components — creating
// this component inline inside PositionsTable triggered the rule because the
// component identity changes on every render.
function SortableHeader({
  field,
  children,
  className = "",
  onSort,
}: {
  field: SortField;
  children: React.ReactNode;
  className?: string;
  onSort: (field: SortField) => void;
}) {
  return (
    <TableHead className={className}>
      <button
        onClick={() => onSort(field)}
        className="flex items-center gap-1 hover:text-foreground transition-colors"
      >
        {children}
        <ArrowUpDown className="h-3 w-3" />
      </button>
    </TableHead>
  );
}

export function PositionsTable({ positions, isLoading }: PositionsTableProps) {
  const [sortField, setSortField] = useState<SortField>("total_pnl");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const toggleRow = (symbol: string) =>
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(symbol)) next.delete(symbol);
      else next.add(symbol);
      return next;
    });

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
    // eslint-disable-next-line security/detect-object-injection -- sortField is typed `keyof Position`, Position is a closed interface
    const aVal = a[sortField];
    // eslint-disable-next-line security/detect-object-injection -- sortField is typed `keyof Position`, Position is a closed interface
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

  return (
    <Card>
      <CardHeader>
        <CardTitle>Open Positions</CardTitle>
        <CardDescription>
          {positions.length} positions • Day change is relative to previous close
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* Mobile (UX study D1): sort chips + two-line rows, no horizontal scroll */}
        <div className="md:hidden">
          <div className="flex items-center gap-2 overflow-x-auto pb-3">
            {MOBILE_SORTS.map(({ field, label }) => {
              const selected = sortField === field;
              return (
                <button
                  key={field}
                  type="button"
                  onClick={() => handleSort(field)}
                  className={`whitespace-nowrap rounded-full border px-3 py-1 text-xs font-semibold transition-colors ${
                    selected
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border bg-card text-muted-foreground"
                  }`}
                >
                  {label}
                  {selected ? (sortOrder === "desc" ? " ↓" : " ↑") : ""}
                </button>
              );
            })}
          </div>
          <div className="border-t">
            {sortedPositions.map((position) => (
              <MobilePositionRow
                key={position.symbol}
                position={position}
                isExpanded={expandedRows.has(position.symbol)}
                onToggle={() => toggleRow(position.symbol)}
              />
            ))}
          </div>
          <div className="flex items-baseline justify-between px-1 pt-3 text-sm font-semibold tabular-nums">
            <span>Total</span>
            <span className={getPnLClass(totals.total_pnl)}>
              {totals.total_pnl >= 0 ? "+" : ""}
              {formatCurrency(totals.total_pnl)} ({formatPercentValue(totalPnlPct)})
            </span>
          </div>
        </div>

        <div className="hidden rounded-md border overflow-x-auto md:block">
          <Table>
            <TableHeader>
              <TableRow>
                <SortableHeader field="symbol" onSort={handleSort}>Symbol</SortableHeader>
                <SortableHeader field="qty" className="text-right" onSort={handleSort}>
                  Qty
                </SortableHeader>
                <SortableHeader field="avg_price" className="text-right" onSort={handleSort}>
                  Entry
                </SortableHeader>
                <SortableHeader field="ltp" className="text-right" onSort={handleSort}>
                  LTP
                </SortableHeader>
                <SortableHeader field="invested" className="text-right" onSort={handleSort}>
                  Invested
                </SortableHeader>
                <SortableHeader field="current_value" className="text-right" onSort={handleSort}>
                  Current
                </SortableHeader>
                <SortableHeader field="total_pnl" className="text-right" onSort={handleSort}>
                  Total P&L
                </SortableHeader>
                <SortableHeader field="total_pnl_pct" className="text-right" onSort={handleSort}>
                  Total %
                </SortableHeader>
                <SortableHeader field="day_pnl" className="text-right" onSort={handleSort}>
                  Day P&L
                </SortableHeader>
                <SortableHeader field="day_pnl_pct" className="text-right" onSort={handleSort}>
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
