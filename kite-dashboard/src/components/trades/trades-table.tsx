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
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useTrades } from "@/lib/hooks";
import type { Trade } from "@/lib/types";
import {
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Search,
} from "lucide-react";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 25;

const inr = (v: number) =>
  v.toLocaleString("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  });

const inrSigned = (v: number) => (v >= 0 ? `+${inr(v)}` : `-${inr(Math.abs(v))}`);

export function TradesTable() {
  const [page, setPage] = useState(0);
  const [symbol, setSymbol] = useState("");
  const [side, setSide] = useState<string>("");
  const [searchInput, setSearchInput] = useState("");
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const toggleExpand = (id: number) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const { data, isLoading, error } = useTrades({
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
    symbol: symbol || undefined,
    side: side || undefined,
  });

  const handleSearch = () => {
    setSymbol(searchInput);
    setPage(0);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  if (isLoading) {
    return <TradesTableSkeleton />;
  }

  if (error) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">Failed to load trades</p>
        </CardContent>
      </Card>
    );
  }

  const trades = data?.trades || [];
  const totalCount = data?.total_count || 0;
  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <CardTitle>Every trade</CardTitle>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search symbol..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyPress={handleKeyPress}
                className="pl-8 w-40"
              />
            </div>
            <Select value={side || "all"} onValueChange={(v) => { setSide(v === "all" ? "" : v); setPage(0); }}>
              <SelectTrigger className="w-24">
                <SelectValue placeholder="Side" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="BUY">Buy</SelectItem>
                <SelectItem value="SELL">Sell</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {trades.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <p>No trades found</p>
            {(symbol || side) && (
              <p className="text-sm mt-1">Try adjusting your filters</p>
            )}
          </div>
        ) : (
          <>
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-8"></TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Symbol</TableHead>
                    <TableHead>Side</TableHead>
                    <TableHead className="text-right">Shares</TableHead>
                    <TableHead className="text-right">Price</TableHead>
                    <TableHead className="text-right">Notional</TableHead>
                    <TableHead className="text-right">Realized P&amp;L</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {trades.map((trade) => (
                    <TradeRow
                      key={trade.id}
                      trade={trade}
                      isExpanded={expanded.has(trade.id)}
                      onToggle={() => toggleExpand(trade.id)}
                    />
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between mt-4">
              <p className="text-sm text-muted-foreground">
                Showing {page * PAGE_SIZE + 1}-{Math.min((page + 1) * PAGE_SIZE, totalCount)} of {totalCount} trades
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => p - 1)}
                  disabled={page === 0}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="text-sm">
                  Page {page + 1} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => p + 1)}
                  disabled={page >= totalPages - 1}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function TradeRow({
  trade,
  isExpanded,
  onToggle,
}: {
  trade: Trade;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const hasMatches = trade.side === "SELL" && (trade.matches?.length ?? 0) > 0;
  const totalPnl =
    trade.matches?.reduce((sum, m) => sum + m.realized_pnl, 0) ?? 0;
  const pnlPositive = totalPnl >= 0;

  return (
    <>
      <TableRow
        className={cn(hasMatches && "cursor-pointer hover:bg-muted/50")}
        onClick={hasMatches ? onToggle : undefined}
      >
        <TableCell className="w-8">
          {hasMatches ? (
            isExpanded ? (
              <ChevronUp className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            )
          ) : null}
        </TableCell>
        <TableCell className="font-mono text-sm">{trade.date}</TableCell>
        <TableCell className="font-medium">{trade.symbol}</TableCell>
        <TableCell>
          <Badge variant={trade.side === "BUY" ? "default" : "destructive"}>
            {trade.side}
          </Badge>
        </TableCell>
        <TableCell className="text-right font-mono">
          {trade.shares.toLocaleString()}
        </TableCell>
        <TableCell className="text-right font-mono">
          {trade.price.toFixed(2)}
        </TableCell>
        <TableCell className="text-right font-mono">
          {inr(trade.notional)}
        </TableCell>
        <TableCell
          className={cn(
            "text-right font-mono",
            hasMatches
              ? pnlPositive
                ? "text-green-600"
                : "text-red-600"
              : "text-muted-foreground"
          )}
        >
          {hasMatches ? inrSigned(totalPnl) : "—"}
        </TableCell>
      </TableRow>
      {hasMatches && isExpanded && (
        <TableRow className="bg-muted/30 hover:bg-muted/30">
          <TableCell colSpan={8} className="p-4">
            <MatchedBuyPanel trade={trade} />
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

function MatchedBuyPanel({ trade }: { trade: Trade }) {
  const matches = trade.matches ?? [];
  if (matches.length === 0) return null;

  const totalPnl = matches.reduce((s, m) => s + m.realized_pnl, 0);
  const totalShares = matches.reduce((s, m) => s + m.shares_matched, 0);
  const weightedEntry =
    totalShares > 0
      ? matches.reduce((s, m) => s + m.entry_price * m.shares_matched, 0) /
        totalShares
      : 0;
  const weightedHold =
    totalShares > 0
      ? matches.reduce((s, m) => s + m.holding_days * m.shares_matched, 0) /
        totalShares
      : 0;
  const exitPrice = trade.notional > 0 ? (trade.notional - trade.slippage) / trade.shares : 0;
  const overallPct =
    weightedEntry > 0 ? (exitPrice / weightedEntry - 1) * 100 : 0;
  const isMulti = matches.length > 1;

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
        <div>
          <div className="text-xs text-muted-foreground">
            Entry Date{isMulti ? " (earliest)" : ""}
          </div>
          <div className="font-mono">{matches[0].entry_date}</div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground">
            Entry Price{isMulti ? " (weighted)" : " (net)"}
          </div>
          <div className="font-mono">{weightedEntry.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground">
            Holding Days{isMulti ? " (weighted)" : ""}
          </div>
          <div className="font-mono">{weightedHold.toFixed(0)}</div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground">Exit Price (net)</div>
          <div className="font-mono">{exitPrice.toFixed(2)}</div>
        </div>
      </div>
      <div className="flex items-center gap-4 pt-2 border-t">
        <div>
          <div className="text-xs text-muted-foreground">Realized P&amp;L</div>
          <div
            className={cn(
              "font-mono text-lg font-semibold",
              totalPnl >= 0 ? "text-green-600" : "text-red-600"
            )}
          >
            {inrSigned(totalPnl)}{" "}
            <span className="text-sm font-normal">
              ({overallPct >= 0 ? "+" : ""}
              {overallPct.toFixed(2)}%)
            </span>
          </div>
        </div>
      </div>
      {isMulti && (
        <div className="pt-2">
          <div className="text-xs text-muted-foreground mb-2">
            Matched across {matches.length} buy lots (FIFO):
          </div>
          <div className="space-y-1 text-xs font-mono">
            {matches.map((m, i) => (
              <div
                key={i}
                className="flex gap-4 items-center justify-between pl-2"
              >
                <span>
                  {m.entry_date} — {m.shares_matched.toLocaleString()} sh @{" "}
                  {m.entry_price.toFixed(2)} ({m.holding_days}d)
                </span>
                <span
                  className={cn(
                    m.realized_pnl >= 0 ? "text-green-600" : "text-red-600"
                  )}
                >
                  {inrSigned(m.realized_pnl)} (
                  {m.realized_pnl_pct >= 0 ? "+" : ""}
                  {m.realized_pnl_pct.toFixed(2)}%)
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function TradesTableSkeleton() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <Skeleton className="h-6 w-32" />
          <div className="flex gap-2">
            <Skeleton className="h-9 w-40" />
            <Skeleton className="h-9 w-24" />
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {[...Array(10)].map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
