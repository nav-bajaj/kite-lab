"use client";

import { useMemo, useRef, useState, useSyncExternalStore } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useRebalanceUpcoming } from "@/lib/hooks";
import type { RebalanceUpcoming } from "@/lib/types";
import { formatCompact } from "@/lib/utils";
import {
  AlertTriangle,
  ArrowDownCircle,
  ArrowUpCircle,
  ChevronDown,
  ChevronUp,
  ListChecks,
} from "lucide-react";

// Subscriber's own portfolio value (₹) — stored client-side and never sent
// to the server (see PLAN.md "Optional ₹ personalization, client-side only").
// Per-universe so it doesn't bleed between portfolios.
const STORAGE_KEY_PREFIX = "rebalance.portfolio_value.";

// localStorage as an external store — useSyncExternalStore handles the
// SSR hydration cleanly (server snapshot is null; client reads the real
// value on mount without the "setState inside useEffect" antipattern).
function subscribeLocalStorage(key: string, cb: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  const handler = (e: StorageEvent) => {
    if (e.key === key) cb();
  };
  window.addEventListener("storage", handler);
  return () => window.removeEventListener("storage", handler);
}

function useClientCapital(universe: string) {
  const storageKey = `${STORAGE_KEY_PREFIX}${universe}`;
  // Bump on writes so useSyncExternalStore re-reads without waiting for a
  // cross-tab "storage" event.
  const versionRef = useRef(0);
  const listenersRef = useRef(new Set<() => void>());

  const subscribe = (cb: () => void) => {
    listenersRef.current.add(cb);
    const unsubExternal = subscribeLocalStorage(storageKey, cb);
    return () => {
      listenersRef.current.delete(cb);
      unsubExternal();
    };
  };
  const getSnapshot = () => {
    // Versioned key so React sees a new identity after persist() bumps it.
    void versionRef.current;
    if (typeof window === "undefined") return null;
    const raw = window.localStorage.getItem(storageKey);
    if (raw === null) return null;
    const n = Number(raw);
    return Number.isFinite(n) && n > 0 ? n : null;
  };
  const getServerSnapshot = () => null;

  const value = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const persist = (n: number | null) => {
    if (typeof window === "undefined") return;
    if (n === null || !Number.isFinite(n) || n <= 0) {
      window.localStorage.removeItem(storageKey);
    } else {
      window.localStorage.setItem(storageKey, String(n));
    }
    versionRef.current += 1;
    listenersRef.current.forEach((cb) => cb());
  };

  return [value, persist] as const;
}

interface SizedBuy {
  symbol: string;
  target_weight: number;
  est_notional: number | null;
  est_shares: number | null;
}

// Re-derive the BUY sizing on the client using the subscriber's own capital.
// Mirrors data_pipeline/rebalance_proposal.build_proposal: est_notional =
// weight × capital; est_shares = round(est_notional / price). We don't ship
// per-symbol prices through the API yet, so when the subscriber supplies
// capital we surface ₹ amounts and scale the producer's share count.
//
// When no capital is set we deliberately show WEIGHT ONLY — the producer's
// est_notional/est_shares are on the model book's ₹ base (~₹10L), not the
// subscriber's, so surfacing them would be misleading (the hint tells the user
// to enter their value to see ₹). See audit U1.
function sizeBuys(
  buys: SizedBuy[],
  modelCapital: number | null,
  clientCapital: number | null,
): SizedBuy[] {
  if (clientCapital === null || modelCapital === null || modelCapital <= 0) {
    return buys.map((b) => ({
      symbol: b.symbol,
      target_weight: b.target_weight,
      est_notional: null,
      est_shares: null,
    }));
  }
  const scale = clientCapital / modelCapital;
  return buys.map((b) => ({
    symbol: b.symbol,
    target_weight: b.target_weight,
    est_notional: b.target_weight * clientCapital,
    // Scale shares proportionally — same rupee per share, more notional →
    // more shares. Floor to avoid overstating.
    est_shares: b.est_shares === null ? null : Math.max(0, Math.floor(b.est_shares * scale)),
  }));
}

export function ActionableTrades() {
  const { data, isLoading, error } = useRebalanceUpcoming();
  const universe = data?.universe ?? "";
  const [clientCapital, setClientCapital] = useClientCapital(universe);
  const [showHolds, setShowHolds] = useState(false);

  const sizedBuys = useMemo(() => {
    if (!data) return [];
    return sizeBuys(data.buys, data.initial_capital, clientCapital);
  }, [data, clientCapital]);

  if (isLoading) return <ActionableSkeleton />;

  if (error || !data) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">
            Failed to load upcoming rebalance.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!data.available) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <ListChecks className="h-5 w-5 text-muted-foreground" />
            <CardTitle>Actionable trades</CardTitle>
          </div>
          <CardDescription>
            No upcoming rebalance has been produced yet for this portfolio.
            The next end-of-day run will populate it on the signal day.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const totalActions = data.sell_count + data.buy_count;

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <ListChecks className="h-5 w-5 text-blue-500" />
            <CardTitle>Actionable trades</CardTitle>
          </div>
          <ActionableMeta data={data} />
        </div>
        <CardDescription>
          {totalActions === 0
            ? "No membership changes at the upcoming rebalance — your model book stays the same."
            : `Trades take effect ${data.exec_date}. Signal data as of ${data.data_as_of}.`}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-5">
        {/* Stale proposal warning (exec_date has passed) */}
        {data.stale && (
          <div className="flex items-start gap-2 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>
              This shows the {data.exec_date} rebalance, whose execution date has
              passed. Your next set of trades will appear here after the upcoming
              signal day.
            </span>
          </div>
        )}

        {/* Regime / risk strip */}
        <RegimeStrip data={data} />

        {/* Optional ₹ personalisation — only useful when there are BUYs to size */}
        {sizedBuys.length > 0 && (
          <PortfolioValueInput
            value={clientCapital}
            onChange={setClientCapital}
          />
        )}

        {/* SELL (full exits) */}
        {data.sells.length > 0 && (
          <section className="space-y-2">
            <SectionTitle
              icon={<ArrowDownCircle className="h-4 w-4 text-red-500" />}
              label="Sell — exit fully"
              count={data.sells.length}
              hint="Sell your entire position in each name."
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

        {/* BUY (new entries) */}
        {sizedBuys.length > 0 && (
          <section className="space-y-2">
            <SectionTitle
              icon={<ArrowUpCircle className="h-4 w-4 text-green-500" />}
              label="Buy — new positions"
              count={sizedBuys.length}
              hint={
                clientCapital !== null
                  ? "Sized to your portfolio value below (approximate)."
                  : "Set your portfolio value below to see ₹ amounts."
              }
            />
            <ul className="space-y-1.5">
              {sizedBuys.map((b) => (
                <li
                  key={`buy-${b.symbol}`}
                  className="flex flex-wrap items-baseline justify-between gap-2 rounded-md border bg-card px-3 py-2"
                >
                  <span className="font-medium">+ {b.symbol}</span>
                  <span className="flex flex-wrap items-baseline gap-3 text-sm text-muted-foreground">
                    <span>{(b.target_weight * 100).toFixed(2)}% target</span>
                    {b.est_notional !== null && (
                      <span>≈ {formatCompact(b.est_notional)}</span>
                    )}
                    {b.est_shares !== null && (
                      <span>
                        ≈ {b.est_shares} share{b.est_shares === 1 ? "" : "s"}
                      </span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* HOLD (collapsed by default) */}
        {data.holds.length > 0 && (
          <section className="space-y-2">
            <button
              type="button"
              className="flex w-full items-center justify-between text-left"
              onClick={() => setShowHolds((v) => !v)}
            >
              <SectionTitle
                icon={<ListChecks className="h-4 w-4 text-muted-foreground" />}
                label={`Hold — ${data.holds.length} continuing position${
                  data.holds.length === 1 ? "" : "s"
                }`}
                hint="No action needed."
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

        {/* Info-only disclaimer next to the imperative instructions */}
        <p className="border-t pt-3 text-xs text-muted-foreground">
          {data.buy_count > 0 && (
            <>
              &ldquo;Target&rdquo; is each name&apos;s share of your portfolio.{" "}
            </>
          )}
          For information only — not a recommendation. Finalises at close.
        </p>
      </CardContent>
    </Card>
  );
}

function ActionableMeta({ data }: { data: RebalanceUpcoming }) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
      <Badge variant="outline">{data.sell_count} sell</Badge>
      <Badge variant="outline">{data.buy_count} buy</Badge>
      <Badge variant="outline">{data.hold_count} hold</Badge>
    </div>
  );
}

function RegimeStrip({ data }: { data: RebalanceUpcoming }) {
  if (
    data.regime === null &&
    (data.drawdown_from_peak === null || data.drawdown_from_peak === undefined)
  ) {
    return null;
  }
  const dd =
    data.drawdown_from_peak !== null && data.drawdown_from_peak !== undefined
      ? data.drawdown_from_peak * 100
      : null;
  const isBear = data.regime === "bear";

  return (
    <div
      className={`space-y-1.5 rounded-md px-3 py-2 text-sm ${
        isBear
          ? "bg-amber-50 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300"
          : "bg-muted/50"
      }`}
    >
      <div className="flex flex-wrap items-center gap-3">
        {data.regime && (
          <span className="flex items-center gap-1.5">
            {isBear && <AlertTriangle className="h-4 w-4" />}
            <span className="text-xs uppercase tracking-wide">Market regime</span>
            <Badge
              variant={isBear ? "outline" : "secondary"}
              className={isBear ? "border-amber-600" : ""}
            >
              {isBear ? "Bear — defensive" : "Bull"}
            </Badge>
          </span>
        )}
        {dd !== null && (
          <span className="text-xs">
            <span className="uppercase tracking-wide">
              Portfolio drawdown from peak
            </span>
            {": "}
            <span className="font-medium">{dd.toFixed(1)}%</span>
          </span>
        )}
      </div>
      {isBear && (
        <p className="text-xs">
          A bear regime means the strategy trims exposure / holds more cash to
          limit losses, so it may hold fewer names than usual.
        </p>
      )}
    </div>
  );
}

function PortfolioValueInput({
  value,
  onChange,
}: {
  value: number | null;
  onChange: (n: number | null) => void;
}) {
  // Uncontrolled: defaultValue keys off `value` and the input remounts on
  // upstream changes via the `key` prop. The Apply / Enter handlers read
  // from the ref so we don't sync draft state inside an effect.
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSave = () => {
    const trimmed = (inputRef.current?.value ?? "").trim();
    if (trimmed === "") {
      onChange(null);
      return;
    }
    const n = Number(trimmed);
    if (Number.isFinite(n) && n > 0) onChange(n);
  };

  return (
    <div className="space-y-1 rounded-md border bg-card px-3 py-2">
      <label
        htmlFor="rebalance-portfolio-value"
        className="text-xs uppercase tracking-wide text-muted-foreground"
      >
        Your portfolio value (₹) — optional, stored on this device only
      </label>
      <div className="flex items-center gap-2">
        <Input
          id="rebalance-portfolio-value"
          key={value ?? "empty"}
          ref={inputRef}
          inputMode="numeric"
          placeholder="e.g. 500000"
          defaultValue={value !== null ? String(value) : ""}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSave();
          }}
          className="max-w-xs"
        />
        <Button type="button" size="sm" onClick={handleSave}>
          Apply
        </Button>
        {value !== null && (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => onChange(null)}
          >
            Clear
          </Button>
        )}
      </div>
    </div>
  );
}

function SectionTitle({
  icon,
  label,
  count,
  hint,
}: {
  icon: React.ReactNode;
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
      <CardHeader>
        <Skeleton className="h-5 w-48" />
        <Skeleton className="h-4 w-72" />
      </CardHeader>
      <CardContent className="space-y-4">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-24 w-full" />
      </CardContent>
    </Card>
  );
}
