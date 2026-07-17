"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useRebalanceSummary, useRebalanceUpcoming } from "@/lib/hooks";
import type { RebalanceNextInfo, RebalanceUpcoming } from "@/lib/types";
import {
  AlertTriangle,
  ArrowDownCircle,
  ArrowUpCircle,
  CalendarClock,
  ChevronDown,
  ChevronUp,
  Sparkles,
} from "lucide-react";

export function ActionableTrades() {
  const { data, isLoading, error } = useRebalanceUpcoming();
  // Shared SWR cache with the history card below — gives us the next signal
  // date, the cadence label and the holdings count at no extra network cost.
  const { data: summary } = useRebalanceSummary();
  const [showHolds, setShowHolds] = useState(false);

  if (isLoading) return <ActionableSkeleton />;

  if (error || !data) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">
            Failed to load upcoming trades.
          </p>
        </CardContent>
      </Card>
    );
  }

  const next = summary?.next ?? null;
  const cadenceLabel = summary?.cadence_label ?? null;
  const holdingsCount = summary?.holdings_count ?? null;
  // A stale proposal (its exec date already passed) is NOT an upcoming trade —
  // it lives in the history below. Only a live, non-empty proposal is "the next
  // trades"; everything else falls through to the countdown.
  const hasMoves =
    data.available && !data.stale && data.sell_count + data.buy_count > 0;

  return (
    <Card className="overflow-hidden">
      {/* Hero banner — the emotional centre of the page. Either the staged
          trades (when a proposal is live) or a countdown to the next signal. */}
      <div className="bg-gradient-to-br from-primary/10 via-primary/5 to-transparent px-6 py-6">
        {hasMoves ? (
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-primary">
              <Sparkles className="h-4 w-4" />
              Your next trades
            </div>
            <p className="text-2xl font-bold tracking-tight">
              {data.buy_count} to buy · {data.sell_count} to sell
            </p>
            <p className="text-sm text-muted-foreground">
              {data.exec_date
                ? `These take effect at the ${data.exec_date} rebalance.`
                : "These take effect at the upcoming rebalance."}
            </p>
          </div>
        ) : (
          <Countdown next={next} />
        )}

        {(cadenceLabel || holdingsCount != null) && (
          <p className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
            {cadenceLabel && (
              <span className="inline-flex items-center gap-1.5">
                <CalendarClock className="h-3.5 w-3.5" />
                Rebalances {cadenceLabel.toLowerCase()}
              </span>
            )}
            {holdingsCount != null && (
              <>
                <span className="opacity-40">·</span>
                <span>{holdingsCount} holdings</span>
              </>
            )}
          </p>
        )}
      </div>

      <CardContent className="space-y-5 pt-5">
        {/* Bear-regime plain-language note (only when defensive) */}
        <RegimeNote data={data} />

        {/* Between-cycles / no-change states */}
        {!hasMoves && (
          <div className="rounded-md border border-dashed px-4 py-6 text-center">
            <p className="text-sm text-muted-foreground">
              {data.available && !data.stale
                ? "No changes this time — the current leaders are holding their spots, so the portfolio stays as-is."
                : "We're between rebalances right now. When the next signal lands, the exact buys and sells will appear here — that's the moment worth watching for. The most recent reshuffle is in the history below."}
            </p>
          </div>
        )}

        {/* SELL (full exits) — only for a live proposal */}
        {hasMoves && data.sells.length > 0 && (
          <section className="space-y-2">
            <SectionTitle
              icon={<ArrowDownCircle className="h-4 w-4 text-red-500" />}
              label="Selling out"
              count={data.sells.length}
              hint="These names leave the portfolio entirely."
            />
            <div className="flex flex-wrap gap-1.5">
              {data.sells.map((s) => (
                <Badge
                  key={`sell-${s}`}
                  variant="outline"
                  className="border-red-500 text-red-700 dark:text-red-400"
                >
                  − {s}
                </Badge>
              ))}
            </div>
          </section>
        )}

        {/* BUY (new entries) — weight only (no per-user ₹ sizing) */}
        {hasMoves && data.buys.length > 0 && (
          <section className="space-y-2">
            <SectionTitle
              icon={<ArrowUpCircle className="h-4 w-4 text-green-500" />}
              label="Buying in"
              count={data.buys.length}
              hint="New names entering the portfolio."
            />
            <ul className="space-y-1.5">
              {data.buys.map((b) => (
                <li
                  key={`buy-${b.symbol}`}
                  className="flex flex-wrap items-baseline justify-between gap-2 rounded-md border bg-card px-3 py-2"
                >
                  <span className="font-medium">+ {b.symbol}</span>
                  <span className="text-sm text-muted-foreground">
                    {(b.target_weight * 100).toFixed(1)}% of the portfolio
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* HOLD (collapsed by default) */}
        {hasMoves && data.holds.length > 0 && (
          <section className="space-y-2">
            <button
              type="button"
              className="flex w-full items-center justify-between text-left"
              onClick={() => setShowHolds((v) => !v)}
            >
              <SectionTitle
                label={`Staying put — ${data.holds.length} name${
                  data.holds.length === 1 ? "" : "s"
                } you already hold`}
              />
              {showHolds ? (
                <ChevronUp className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              )}
            </button>
            {showHolds && (
              <div className="flex flex-wrap gap-1.5">
                {data.holds.map((s) => (
                  <Badge key={`hold-${s}`} variant="secondary">
                    {s}
                  </Badge>
                ))}
              </div>
            )}
          </section>
        )}

        {/* Disclaimer */}
        <p className="border-t pt-3 text-xs text-muted-foreground">
          A model portfolio for education — not a recommendation to trade. The
          exact list is finalised at market close on the signal day.
        </p>
      </CardContent>
    </Card>
  );
}

function Countdown({ next }: { next: RebalanceNextInfo | null }) {
  if (!next) {
    return (
      <div className="space-y-1">
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-primary">
          <CalendarClock className="h-4 w-4" />
          Next set of trades
        </div>
        <p className="text-lg font-semibold">Coming soon</p>
        <p className="text-sm text-muted-foreground">
          Not enough history yet to project the next rebalance date.
        </p>
      </div>
    );
  }

  const days = next.trading_days_until;
  const today = days <= 0;

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-primary">
        <CalendarClock className="h-4 w-4" />
        Next set of trades
      </div>
      {today ? (
        <p className="text-2xl font-bold tracking-tight">Landing today</p>
      ) : (
        <p className="text-2xl font-bold tracking-tight">
          {days} trading day{days === 1 ? "" : "s"} away
        </p>
      )}
      <p className="text-sm text-muted-foreground">
        Next signal on {next.signal_date}
        {!today && " — check back then to see the exact buys and sells."}
      </p>
    </div>
  );
}

function RegimeNote({ data }: { data: RebalanceUpcoming }) {
  if (data.regime !== "bear") return null;
  return (
    <div className="flex items-start gap-2 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
      <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span>
        Defensive mode: the broad market is weak, so the strategy is holding more
        cash and fewer names than usual to limit losses.
      </span>
    </div>
  );
}

function SectionTitle({
  icon,
  label,
  count,
  hint,
}: {
  icon?: React.ReactNode;
  label: string;
  count?: number;
  hint?: string;
}) {
  return (
    <div className="flex flex-wrap items-baseline gap-2">
      <span className="flex items-center gap-1.5 font-medium">
        {icon}
        {label}
        {count !== undefined && (
          <span className="text-muted-foreground">({count})</span>
        )}
      </span>
      {hint && <span className="text-xs text-muted-foreground">{hint}</span>}
    </div>
  );
}

function ActionableSkeleton() {
  return (
    <Card>
      <div className="bg-muted/40 px-6 py-6">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="mt-2 h-8 w-56" />
        <Skeleton className="mt-2 h-4 w-72" />
      </div>
      <CardContent className="space-y-4 pt-5">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-24 w-full" />
      </CardContent>
    </Card>
  );
}
