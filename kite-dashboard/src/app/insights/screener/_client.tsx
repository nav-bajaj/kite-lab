"use client";

import { useMemo, useState, useCallback } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  StockRow,
  fmtPct,
  fmtNum,
  sectorLabel,
} from "@/lib/insights-api";
import { Pct, Tag, ScoreBar, volumeBandTone } from "@/components/insights/ui";
import { TagBadges } from "@/components/insights/tag-badges";
import { cn } from "@/lib/utils";

/**
 * The NSE 500 screener. One payload from the server, all filtering / sorting /
 * presets happen client-side. Filter state is mirrored into the URL query
 * (via history.replaceState — no server round-trip) so any view is shareable
 * and bookmarkable; the `date` snapshot param is preserved untouched.
 *
 * Compliance: every rendered tag / band string comes verbatim from the engine
 * (StockRow.tags / extension_band / volume_band). No column implies an action.
 * The "Fresh momentum" preset is observation-only (its cohort failed the
 * forward-return validity study) — labelled as such, no performance claim.
 */

type OptionalGroup = "risk" | "volume";

interface Filters {
  sectors: string[];
  tags: string[];
  rankMax: string;
  trendMin: string;
  consMin: string;
  r1m: string;
  r3m: string;
  r6m: string;
  atrMax: string;
  nearHigh: string; // within X% of the 52w high
  volMin: string;
  above50: boolean;
  above200: boolean;
}

const EMPTY: Filters = {
  sectors: [],
  tags: [],
  rankMax: "",
  trendMin: "",
  consMin: "",
  r1m: "",
  r3m: "",
  r6m: "",
  atrMax: "",
  nearHigh: "",
  volMin: "",
  above50: false,
  above200: false,
};

interface Preset {
  key: string;
  label: string;
  note?: string;
  patch: Partial<Filters>;
}

// Presets encode transparent filter combos (mostly engine tags, whose
// thresholds are documented in the Learn layer). Shareable via ?preset=.
const PRESETS: Preset[] = [
  { key: "leaders", label: "Momentum leaders", patch: { tags: ["Momentum leader"] } },
  {
    key: "fresh",
    label: "Fresh momentum",
    note: "Observation only — biggest RS-rank improvers. Not a forward-return signal.",
    patch: { tags: ["New momentum"] },
  },
  { key: "near-high", label: "Near 52w highs", patch: { tags: ["Near 52-week high"] } },
  { key: "vol-surge", label: "Volume surges", patch: { tags: ["Volume expansion"] } },
  {
    key: "quiet",
    label: "Quiet compounders",
    patch: { tags: ["Quiet"], consMin: "60" },
  },
  {
    key: "extended",
    label: "Extended names",
    note: "Descriptive state (stretched vs own history) — not a mean-reversion call.",
    patch: { tags: ["Extended"] },
  },
];

interface Column {
  id: string;
  label: string;
  group: "rs" | "returns" | "trend" | "risk" | "volume";
  learn?: string;
  sortField?: keyof StockRow;
  align?: "left" | "right";
  render: (r: StockRow) => React.ReactNode;
}

// Prefer the per-stock Zerodha sector (covers ~100% of the NSE 500); fall back
// to the NSE index-basket label only if it's missing.
const secText = (r: StockRow) =>
  r.zerodha_sector ?? (r.sectors.length ? sectorLabel(r.sectors[0]) : "—");
const num = (v: number | null | undefined, d = 2) => fmtNum(v, d);

const COLUMNS: Column[] = [
  // RS + the two Marketworks scores, kept together next to RS rank
  { id: "rank", label: "RS rank", group: "rs", learn: "rs-rank", sortField: "rank", align: "right",
    render: (r) => (r.rank ?? "—") },
  { id: "percentile", label: "RS %ile", group: "rs", learn: "rs-rank", sortField: "percentile", align: "right",
    render: (r) => (r.percentile === null ? "—" : r.percentile.toFixed(0)) },
  { id: "rank_delta_21d", label: "RS rank Δ 21d", group: "rs", learn: "rs-rank", sortField: "rank_delta_21d", align: "right",
    render: (r) => (r.rank_delta_21d === null ? "—" : (r.rank_delta_21d > 0 ? `+${r.rank_delta_21d}` : `${r.rank_delta_21d}`)) },
  { id: "trend_score", label: "Trend", group: "trend", learn: "trend-score", sortField: "trend_score",
    render: (r) => <ScoreBar value={r.trend_score} tone="positive" /> },
  { id: "momentum_consistency", label: "Consistency", group: "trend", learn: "momentum-consistency", sortField: "momentum_consistency",
    render: (r) => <ScoreBar value={r.momentum_consistency} tone="positive" /> },
  // Returns
  { id: "ret_1d", label: "1D", group: "returns", sortField: "ret_1d", align: "right", render: (r) => <Pct v={r.ret_1d} decimals={2} /> },
  { id: "ret_1w", label: "1W", group: "returns", sortField: "ret_1w", align: "right", render: (r) => <Pct v={r.ret_1w} /> },
  { id: "ret_1m", label: "1M", group: "returns", sortField: "ret_1m", align: "right", render: (r) => <Pct v={r.ret_1m} /> },
  { id: "ret_3m", label: "3M", group: "returns", sortField: "ret_3m", align: "right", render: (r) => <Pct v={r.ret_3m} /> },
  { id: "ret_6m", label: "6M", group: "returns", sortField: "ret_6m", align: "right", render: (r) => <Pct v={r.ret_6m} /> },
  { id: "ret_12m", label: "12M", group: "returns", sortField: "ret_12m", align: "right", render: (r) => <Pct v={r.ret_12m} /> },
  // Trend position
  { id: "dist_52w_high_pct", label: "52w high", group: "trend", sortField: "dist_52w_high_pct", align: "right", render: (r) => <Pct v={r.dist_52w_high_pct} /> },
  // Risk
  { id: "extension_band", label: "Extension", group: "risk", learn: "extension-risk", sortField: "extension_risk",
    render: (r) => (r.extension_band ? <Tag label={r.extension_band} /> : "—") },
  { id: "atr_pct", label: "ATR %", group: "risk", learn: "atr", sortField: "atr_pct", align: "right",
    render: (r) => (r.atr_pct === null ? "—" : `${(r.atr_pct * 100).toFixed(1)}%`) },
  { id: "vol_percentile_1y", label: "Vol %ile", group: "risk", sortField: "vol_percentile_1y", align: "right",
    render: (r) => (r.vol_percentile_1y === null ? "—" : `${(r.vol_percentile_1y * 100).toFixed(0)}`) },
  { id: "beta_60d", label: "Beta", group: "risk", learn: "beta", sortField: "beta_60d", align: "right", render: (r) => num(r.beta_60d) },
  { id: "max_drawdown_1y_pct", label: "Max DD 1y", group: "risk", sortField: "max_drawdown_1y_pct", align: "right", render: (r) => <Pct v={r.max_drawdown_1y_pct} /> },
  // Volume
  { id: "vol_ratio", label: "Vol ratio", group: "volume", learn: "volume-confirmation", sortField: "vol_ratio", align: "right",
    render: (r) => (r.vol_ratio === null ? "—" : `${r.vol_ratio.toFixed(1)}x`) },
  { id: "volume_band", label: "Vol conf", group: "volume", learn: "volume-confirmation", sortField: "volume_confirmation",
    render: (r) => (r.volume_band ? <Tag label={r.volume_band} tone={volumeBandTone(r.volume_band)} /> : "—") },
  { id: "avg_turnover_20d_cr", label: "Turnover ₹Cr", group: "volume", sortField: "avg_turnover_20d_cr", align: "right",
    render: (r) => num(r.avg_turnover_20d_cr, 1) },
  { id: "liquidity_tier", label: "Liquidity", group: "volume", learn: "liquidity", sortField: "liquidity_tier",
    render: (r) => r.liquidity_tier ?? "—" },
];

const PAGE_SIZE = 50;

export function ScreenerClient({ rows, asof }: { rows: StockRow[]; asof: string | null }) {
  const searchParams = useSearchParams();

  const [filters, setFilters] = useState<Filters>(() => decodeFilters(searchParams));
  const [groups, setGroups] = useState<Set<OptionalGroup>>(
    () => decodeGroups(searchParams),
  );
  const [sort, setSort] = useState<{ key: keyof StockRow; dir: "asc" | "desc" }>(
    () => decodeSort(searchParams),
  );
  const [activePreset, setActivePreset] = useState<string | null>(
    () => searchParams.get("preset"),
  );
  // Pagination (2026-07-26): ~500 names rendered at once made the page heavy
  // and endless, especially on mobile. Filter/preset/sort changes jump back
  // to page 1; the index also self-clamps when a filter shrinks the results.
  const [page, setPage] = useState(0);

  // Push the current view into the URL without a navigation / refetch.
  const syncUrl = useCallback(
    (f: Filters, g: Set<OptionalGroup>, s: typeof sort, preset: string | null) => {
      if (typeof window === "undefined") return;
      const params = new URLSearchParams(searchParams.toString());
      encodeInto(params, f, g, s, preset);
      const qs = params.toString();
      window.history.replaceState(null, "", qs ? `?${qs}` : window.location.pathname);
    },
    [searchParams],
  );

  const applyPreset = useCallback(
    (p: Preset) => {
      const next = { ...EMPTY, ...p.patch };
      setFilters(next);
      setActivePreset(p.key);
      setPage(0);
      syncUrl(next, groups, sort, p.key);
    },
    [groups, sort, syncUrl],
  );

  const reset = useCallback(() => {
    setFilters(EMPTY);
    setActivePreset(null);
    setPage(0);
    syncUrl(EMPTY, groups, sort, null);
  }, [groups, sort, syncUrl]);

  const toggleGroup = useCallback(
    (g: OptionalGroup) => {
      setGroups((prev) => {
        const next = new Set(prev);
        if (next.has(g)) next.delete(g);
        else next.add(g);
        syncUrl(filters, next, sort, activePreset);
        return next;
      });
    },
    [filters, sort, activePreset, syncUrl],
  );

  const applySort = useCallback(
    (key: keyof StockRow) => {
      setPage(0);
      setSort((prev) => {
        const dir: "asc" | "desc" =
          prev.key === key ? (prev.dir === "asc" ? "desc" : "asc") : "asc";
        const next = { key, dir };
        syncUrl(filters, groups, next, activePreset);
        return next;
      });
    },
    [filters, groups, activePreset, syncUrl],
  );

  const visibleColumns = useMemo(
    () => COLUMNS.filter((c) => c.group === "rs" || c.group === "returns" || c.group === "trend" || groups.has(c.group as OptionalGroup)),
    [groups],
  );

  const filtered = useMemo(() => matchFilters(rows, filters), [rows, filters]);
  const sorted = useMemo(() => sortRows(filtered, sort), [filtered, sort]);

  const pageCount = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const paged = useMemo(
    () => sorted.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE),
    [sorted, safePage],
  );

  const activeNote = PRESETS.find((p) => p.key === activePreset)?.note;

  return (
    <main className="flex flex-col gap-6">
      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="text-2xl font-semibold tracking-[-0.01em] text-foreground">
            NSE 500 screener
          </h2>
          <p className="max-w-3xl text-[13px] leading-[1.55] text-muted-foreground">
            {asof && `As of ${new Date(asof).toLocaleDateString("en-IN")}. `}
            Every NSE 500 stock, scored by the same signals our portfolios use.
            Sort, filter, and share any view. Educational context only — not buy
            or sell recommendations.
          </p>
        </div>

        {/* The three signature Marketworks scores — proprietary, built in-house. */}
        <div className="flex flex-col gap-4 rounded-xl border border-border bg-card p-5">
          <div className="flex flex-col gap-1">
            <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">
              Marketworks scores · built in-house
            </span>
            <p className="max-w-3xl text-[13px] leading-[1.55] text-muted-foreground">
              We grade every stock on three momentum signals we built ourselves.
              You won&apos;t find these exact numbers anywhere else — they&apos;re
              the same scores our portfolios are built on.
            </p>
          </div>
          <dl className="grid gap-5 border-t border-border pt-4 sm:grid-cols-3">
            {[
              {
                term: "RS rank",
                def: "Relative strength rank. We rank all 500 stocks by momentum and give each its place — rank 1 is the single strongest name in the market, higher numbers are weaker.",
                learn: "rs-rank",
              },
              {
                term: "Trend",
                def: "A 0–100 score of how clean and orderly a stock's uptrend is. A high score means it's climbing steadily rather than lurching up and down.",
                learn: "trend-score",
              },
              {
                term: "Consistency",
                def: "A 0–100 score of how reliably a stock has held its momentum over time, rather than owing it all to one sudden jump.",
                learn: "momentum-consistency",
              },
            ].map((s) => (
              <div key={s.term} className="flex flex-col gap-1.5">
                <dt className="text-sm font-semibold text-foreground">{s.term}</dt>
                <dd className="text-[13px] leading-[1.5] text-muted-foreground">{s.def}</dd>
                <Link
                  href={`/insights/learn/${s.learn}`}
                  className="mt-0.5 inline-flex w-fit items-center gap-1 text-[12px] font-medium text-primary underline-offset-2 hover:underline"
                >
                  How we build this
                  <span aria-hidden>→</span>
                </Link>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* Presets */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          Presets
        </span>
        {PRESETS.map((p) => (
          <button
            key={p.key}
            onClick={() => applyPreset(p)}
            className={cn(
              "rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors",
              activePreset === p.key
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            {p.label}
          </button>
        ))}
        <button
          onClick={reset}
          className="rounded-lg px-3 py-1.5 text-xs font-medium text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
        >
          Clear
        </button>
      </div>
      {activeNote && (
        <p className="-mt-3 text-[12px] italic text-muted-foreground">{activeNote}</p>
      )}

      <div className="flex flex-col gap-6">
        {/* Table + group toggles */}
        <div className="min-w-0 flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                Columns
              </span>
              {(["risk", "volume"] as OptionalGroup[]).map((g) => (
                <button
                  key={g}
                  onClick={() => toggleGroup(g)}
                  className={cn(
                    "rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors",
                    groups.has(g)
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border text-muted-foreground hover:bg-muted hover:text-foreground",
                  )}
                >
                  + {g === "risk" ? "Risk" : "Volume"}
                </button>
              ))}
            </div>
            <span className="text-[13px] text-muted-foreground">
              {sorted.length} of {rows.length} names
            </span>
          </div>

          <p className="text-[12px] text-muted-foreground">
            Some stocks carry small badges under their name — hover any badge to
            see what it flags. Tap a column header to sort.
          </p>

          {/* Desktop table */}
          <div className="hidden overflow-x-auto rounded-xl border border-border bg-card md:block">
            <table className="w-full text-[13px]">
              <thead className="border-b border-border bg-muted text-left">
                <tr>
                  <SortableTh label="Symbol" onSort={() => applySort("symbol")} sort={sort} sortField="symbol" />
                  <th className="px-3 py-2 font-semibold text-foreground">Sector</th>
                  {visibleColumns.map((c) => (
                    <SortableTh
                      key={c.id}
                      label={c.label}
                      learn={c.learn}
                      align={c.align}
                      onSort={c.sortField ? () => applySort(c.sortField!) : undefined}
                      sort={sort}
                      sortField={c.sortField}
                    />
                  ))}
                </tr>
              </thead>
              <tbody>
                {paged.map((r, i) => (
                  <tr
                    key={r.symbol}
                    className={cn(
                      "border-b border-border last:border-0 transition-colors hover:bg-primary/[0.06]",
                      i % 2 === 1 && "bg-muted/50",
                    )}
                  >
                    <td className="px-3 py-2">
                      <div className="flex flex-col gap-1">
                        <Link href={`/insights/stocks/${r.symbol}${asofQuery(searchParams)}`} className="font-medium text-foreground underline-offset-2 hover:underline">
                          {r.symbol}
                        </Link>
                        <TagBadges tags={r.tags} />
                      </div>
                    </td>
                    <td className="px-3 py-2 text-xs text-foreground">{secText(r)}</td>
                    {visibleColumns.map((c) => (
                      <td key={c.id} className={cn("px-3 py-2 tabular-nums text-foreground", c.align === "right" ? "text-right" : "text-left")}>
                        {c.render(r)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile card list */}
          <div className="flex flex-col gap-3 md:hidden">
            {paged.map((r) => (
              <MobileCard key={r.symbol} r={r} href={`/insights/stocks/${r.symbol}${asofQuery(searchParams)}`} />
            ))}
          </div>

          {sorted.length === 0 && (
            <p className="text-sm text-muted-foreground">No names match these filters.</p>
          )}

          {pageCount > 1 && (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span className="text-[13px] text-muted-foreground tabular-nums">
                Showing {safePage * PAGE_SIZE + 1}–{Math.min((safePage + 1) * PAGE_SIZE, sorted.length)} of {sorted.length}
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setPage(safePage - 1)}
                  disabled={safePage === 0}
                  className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:pointer-events-none disabled:opacity-40"
                >
                  ← Prev
                </button>
                <span className="text-[13px] text-muted-foreground tabular-nums">
                  Page {safePage + 1} of {pageCount}
                </span>
                <button
                  type="button"
                  onClick={() => setPage(safePage + 1)}
                  disabled={safePage >= pageCount - 1}
                  className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:pointer-events-none disabled:opacity-40"
                >
                  Next →
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

// ─────────────────────────── sub-components ───────────────────────────

function SortableTh({
  label,
  learn,
  align,
  onSort,
  sort,
  sortField,
}: {
  label: string;
  learn?: string;
  align?: "left" | "right";
  onSort?: () => void;
  sort: { key: keyof StockRow; dir: "asc" | "desc" };
  sortField?: keyof StockRow;
}) {
  const active = sortField && sort.key === sortField;
  return (
    <th className={cn("px-3 py-2 font-semibold text-foreground", align === "right" ? "text-right" : "text-left")}>
      <span className={cn("inline-flex items-center gap-1", align === "right" && "justify-end")}>
        {onSort ? (
          <button onClick={onSort} className="inline-flex items-center gap-0.5 hover:text-foreground">
            {label}
            {active && <span aria-hidden>{sort.dir === "asc" ? "▲" : "▼"}</span>}
          </button>
        ) : (
          label
        )}
        {learn && (
          <Link
            href={`/insights/learn/${learn}`}
            title="What is this?"
            className="text-[10px] text-muted-foreground hover:text-foreground"
          >
            ⓘ
          </Link>
        )}
      </span>
    </th>
  );
}

function MobileCard({ r, href }: { r: StockRow; href: string }) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <Link href={href} className="font-medium text-foreground underline-offset-2 hover:underline">
            {r.symbol}
          </Link>
          <span className="text-xs text-muted-foreground">{secText(r)}</span>
        </div>
        <div className="text-right">
          <div className="font-mono text-sm text-foreground">{fmtNum(r.close, 2)}</div>
          <div className="text-xs"><Pct v={r.ret_1d} decimals={2} /></div>
        </div>
      </div>
      {r.tags.length > 0 && (
        <div className="mt-2">
          <TagBadges tags={r.tags} />
        </div>
      )}
      <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
        <Stat label="RS rank" value={r.rank ?? "—"} />
        <Stat label="Trend" value={r.trend_score === null ? "—" : r.trend_score.toFixed(0)} />
        <Stat label="1M" value={fmtPct(r.ret_1m, 1, true)} />
        <Stat label="3M" value={fmtPct(r.ret_3m, 1, true)} />
        <Stat label="6M" value={fmtPct(r.ret_6m, 1, true)} />
        <Stat label="52w high" value={fmtPct(r.dist_52w_high_pct, 1, true)} />
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</span>
      <span className="tabular-nums text-foreground">{value}</span>
    </div>
  );
}

// ─────────────────────────── logic ───────────────────────────

function matchFilters(rows: StockRow[], f: Filters): StockRow[] {
  const rankMax = numOr(f.rankMax);
  const trendMin = numOr(f.trendMin);
  const consMin = numOr(f.consMin);
  const r1m = numOr(f.r1m);
  const r3m = numOr(f.r3m);
  const r6m = numOr(f.r6m);
  const atrMax = numOr(f.atrMax);
  const nearHigh = numOr(f.nearHigh);
  const volMin = numOr(f.volMin);

  return rows.filter((r) => {
    if (f.sectors.length && !r.sectors.some((s) => f.sectors.includes(s))) return false;
    if (f.tags.length && !f.tags.every((t) => r.tags.includes(t))) return false;
    if (rankMax !== null && (r.rank === null || r.rank > rankMax)) return false;
    if (trendMin !== null && (r.trend_score === null || r.trend_score < trendMin)) return false;
    if (consMin !== null && (r.momentum_consistency === null || r.momentum_consistency < consMin)) return false;
    if (r1m !== null && (r.ret_1m === null || r.ret_1m * 100 < r1m)) return false;
    if (r3m !== null && (r.ret_3m === null || r.ret_3m * 100 < r3m)) return false;
    if (r6m !== null && (r.ret_6m === null || r.ret_6m * 100 < r6m)) return false;
    if (atrMax !== null && (r.atr_pct === null || r.atr_pct * 100 > atrMax)) return false;
    if (nearHigh !== null && (r.dist_52w_high_pct === null || r.dist_52w_high_pct * 100 < -nearHigh)) return false;
    if (volMin !== null && (r.vol_ratio === null || r.vol_ratio < volMin)) return false;
    if (f.above50 && !(r.dist_50dma_pct !== null && r.dist_50dma_pct >= 0)) return false;
    if (f.above200 && !(r.dist_200dma_pct !== null && r.dist_200dma_pct >= 0)) return false;
    return true;
  });
}

function sortRows(rows: StockRow[], sort: { key: keyof StockRow; dir: "asc" | "desc" }): StockRow[] {
  const { key, dir } = sort;
  const mul = dir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    // key is a keyof StockRow literal from our own column registry — safe.
    // eslint-disable-next-line security/detect-object-injection
    const av = a[key];
    // eslint-disable-next-line security/detect-object-injection
    const bv = b[key];
    // Nulls always sort last regardless of direction.
    const an = av === null || av === undefined;
    const bn = bv === null || bv === undefined;
    if (an && bn) return 0;
    if (an) return 1;
    if (bn) return -1;
    if (typeof av === "string" && typeof bv === "string") return av.localeCompare(bv) * mul;
    return ((av as number) - (bv as number)) * mul;
  });
}

function numOr(s: string): number | null {
  if (s === "" || s === null) return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

// ─────────────────────────── URL codec ───────────────────────────

function asofQuery(sp: URLSearchParams): string {
  const d = sp.get("date");
  return d ? `?date=${encodeURIComponent(d)}` : "";
}

function decodeFilters(sp: URLSearchParams): Filters {
  return {
    sectors: splitList(sp.get("sec")),
    tags: splitList(sp.get("tags")),
    rankMax: sp.get("rankMax") ?? "",
    trendMin: sp.get("trendMin") ?? "",
    consMin: sp.get("consMin") ?? "",
    r1m: sp.get("r1m") ?? "",
    r3m: sp.get("r3m") ?? "",
    r6m: sp.get("r6m") ?? "",
    atrMax: sp.get("atrMax") ?? "",
    nearHigh: sp.get("nearHigh") ?? "",
    volMin: sp.get("volMin") ?? "",
    above50: sp.get("a50") === "1",
    above200: sp.get("a200") === "1",
  };
}

function decodeGroups(sp: URLSearchParams): Set<OptionalGroup> {
  const g = splitList(sp.get("cols"));
  return new Set(g.filter((x): x is OptionalGroup => x === "risk" || x === "volume"));
}

function decodeSort(sp: URLSearchParams): { key: keyof StockRow; dir: "asc" | "desc" } {
  const raw = sp.get("sort");
  if (raw) {
    const [key, dir] = raw.split(":");
    if (key) return { key: key as keyof StockRow, dir: dir === "desc" ? "desc" : "asc" };
  }
  return { key: "rank", dir: "asc" };
}

function encodeInto(
  params: URLSearchParams,
  f: Filters,
  g: Set<OptionalGroup>,
  s: { key: keyof StockRow; dir: "asc" | "desc" },
  preset: string | null,
) {
  const setOrDel = (k: string, v: string) => (v ? params.set(k, v) : params.delete(k));
  setOrDel("sec", f.sectors.join(","));
  setOrDel("tags", f.tags.join(","));
  setOrDel("rankMax", f.rankMax);
  setOrDel("trendMin", f.trendMin);
  setOrDel("consMin", f.consMin);
  setOrDel("r1m", f.r1m);
  setOrDel("r3m", f.r3m);
  setOrDel("r6m", f.r6m);
  setOrDel("atrMax", f.atrMax);
  setOrDel("nearHigh", f.nearHigh);
  setOrDel("volMin", f.volMin);
  setOrDel("a50", f.above50 ? "1" : "");
  setOrDel("a200", f.above200 ? "1" : "");
  setOrDel("cols", Array.from(g).join(","));
  params.set("sort", `${String(s.key)}:${s.dir}`);
  setOrDel("preset", preset ?? "");
}

function splitList(v: string | null): string[] {
  return v ? v.split(",").filter(Boolean) : [];
}
