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

const ALL_TAGS = [
  "Momentum leader",
  "Near 52-week high",
  "Fresh 52-week high",
  "Volume expansion",
  "Extended",
  "Coiled",
  "New momentum",
  "Quiet",
] as const;

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

const secText = (r: StockRow) => (r.sectors.length ? sectorLabel(r.sectors[0]) : "—");
const num = (v: number | null | undefined, d = 2) => fmtNum(v, d);

const COLUMNS: Column[] = [
  // RS
  { id: "rank", label: "RS rank", group: "rs", learn: "rs-rank", sortField: "rank", align: "right",
    render: (r) => (r.rank ?? "—") },
  { id: "percentile", label: "RS %ile", group: "rs", learn: "rs-rank", sortField: "percentile", align: "right",
    render: (r) => (r.percentile === null ? "—" : r.percentile.toFixed(0)) },
  { id: "sector_rank", label: "Sec rank", group: "rs", learn: "rs-rank", sortField: "sector_rank", align: "right",
    render: (r) => (r.sector_rank && r.sector_size ? `${r.sector_rank}/${r.sector_size}` : "—") },
  { id: "rank_delta_21d", label: "Δ 21d", group: "rs", learn: "rs-rank", sortField: "rank_delta_21d", align: "right",
    render: (r) => (r.rank_delta_21d === null ? "—" : (r.rank_delta_21d > 0 ? `+${r.rank_delta_21d}` : `${r.rank_delta_21d}`)) },
  // Returns
  { id: "ret_1d", label: "1D", group: "returns", sortField: "ret_1d", align: "right", render: (r) => <Pct v={r.ret_1d} decimals={2} /> },
  { id: "ret_1w", label: "1W", group: "returns", sortField: "ret_1w", align: "right", render: (r) => <Pct v={r.ret_1w} /> },
  { id: "ret_1m", label: "1M", group: "returns", sortField: "ret_1m", align: "right", render: (r) => <Pct v={r.ret_1m} /> },
  { id: "ret_3m", label: "3M", group: "returns", sortField: "ret_3m", align: "right", render: (r) => <Pct v={r.ret_3m} /> },
  { id: "ret_6m", label: "6M", group: "returns", sortField: "ret_6m", align: "right", render: (r) => <Pct v={r.ret_6m} /> },
  { id: "ret_12m", label: "12M", group: "returns", sortField: "ret_12m", align: "right", render: (r) => <Pct v={r.ret_12m} /> },
  // Trend
  { id: "trend_score", label: "Trend", group: "trend", learn: "trend-score", sortField: "trend_score",
    render: (r) => <ScoreBar value={r.trend_score} tone="positive" /> },
  { id: "momentum_consistency", label: "Consistency", group: "trend", learn: "momentum-consistency", sortField: "momentum_consistency",
    render: (r) => <ScoreBar value={r.momentum_consistency} tone="positive" /> },
  { id: "dist_50dma_pct", label: "50-DMA", group: "trend", sortField: "dist_50dma_pct", align: "right", render: (r) => <Pct v={r.dist_50dma_pct} /> },
  { id: "dist_200dma_pct", label: "200-DMA", group: "trend", sortField: "dist_200dma_pct", align: "right", render: (r) => <Pct v={r.dist_200dma_pct} /> },
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

  const update = useCallback(
    (patch: Partial<Filters>, preset: string | null = null) => {
      setFilters((prev) => {
        const next = { ...prev, ...patch };
        setActivePreset(preset);
        syncUrl(next, groups, sort, preset);
        return next;
      });
    },
    [groups, sort, syncUrl],
  );

  const applyPreset = useCallback(
    (p: Preset) => {
      const next = { ...EMPTY, ...p.patch };
      setFilters(next);
      setActivePreset(p.key);
      syncUrl(next, groups, sort, p.key);
    },
    [groups, sort, syncUrl],
  );

  const reset = useCallback(() => {
    setFilters(EMPTY);
    setActivePreset(null);
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

  const availableSectors = useMemo(() => {
    const set = new Set<string>();
    rows.forEach((r) => r.sectors.forEach((s) => set.add(s)));
    return Array.from(set).sort();
  }, [rows]);

  const visibleColumns = useMemo(
    () => COLUMNS.filter((c) => c.group === "rs" || c.group === "returns" || c.group === "trend" || groups.has(c.group as OptionalGroup)),
    [groups],
  );

  const filtered = useMemo(() => matchFilters(rows, filters), [rows, filters]);
  const sorted = useMemo(() => sortRows(filtered, sort), [filtered, sort]);

  const activeNote = PRESETS.find((p) => p.key === activePreset)?.note;

  return (
    <main className="flex flex-col gap-6">
      <section className="flex flex-col gap-1">
        <h2 className="font-serif text-2xl font-medium tracking-[-0.01em] text-foreground">
          NSE 500 screener
        </h2>
        <p className="max-w-3xl text-[13px] leading-[1.55] text-muted-foreground">
          {asof && `As of ${new Date(asof).toLocaleDateString("en-IN")}. `}
          Decision-support data on every NSE 500 name — relative strength, trend
          and momentum scores, extension and volume state. Sort, filter, and
          share any view. Educational context only; not buy or sell
          recommendations.
        </p>
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

      <div className="flex flex-col gap-6 lg:flex-row">
        {/* Filter rail */}
        <FilterRail
          filters={filters}
          update={update}
          availableSectors={availableSectors}
        />

        {/* Table + group toggles */}
        <div className="min-w-0 flex-1 flex flex-col gap-3">
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

          {/* Desktop table */}
          <div className="hidden overflow-x-auto rounded-xl border border-border md:block">
            <table className="w-full text-[13px]">
              <thead className="border-b border-border bg-muted/40 text-left">
                <tr>
                  <SortableTh label="Symbol" onSort={() => applySort("symbol")} sort={sort} sortField="symbol" />
                  <th className="px-3 py-2 font-medium text-muted-foreground">Sector</th>
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
                {sorted.map((r) => (
                  <tr key={r.symbol} className="border-b border-border last:border-0 hover:bg-muted/30">
                    <td className="px-3 py-2">
                      <div className="flex flex-col gap-1">
                        <Link href={`/insights/stocks/${r.symbol}${asofQuery(searchParams)}`} className="font-medium text-foreground underline-offset-2 hover:underline">
                          {r.symbol}
                        </Link>
                        {r.tags.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {r.tags.map((t) => <Tag key={t} label={t} />)}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-2 text-xs text-muted-foreground">{secText(r)}</td>
                    {visibleColumns.map((c) => (
                      <td key={c.id} className={cn("px-3 py-2 tabular-nums", c.align === "right" ? "text-right" : "text-left")}>
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
            {sorted.map((r) => (
              <MobileCard key={r.symbol} r={r} href={`/insights/stocks/${r.symbol}${asofQuery(searchParams)}`} />
            ))}
          </div>

          {sorted.length === 0 && (
            <p className="text-sm text-muted-foreground">No names match these filters.</p>
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
    <th className={cn("px-3 py-2 font-medium text-muted-foreground", align === "right" ? "text-right" : "text-left")}>
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
          <span className="text-xs text-muted-foreground">
            {r.sectors.length ? sectorLabel(r.sectors[0]) : "—"}
          </span>
        </div>
        <div className="text-right">
          <div className="font-mono text-sm text-foreground">{fmtNum(r.close, 2)}</div>
          <div className="text-xs"><Pct v={r.ret_1d} decimals={2} /></div>
        </div>
      </div>
      {r.tags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {r.tags.map((t) => <Tag key={t} label={t} />)}
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

function FilterRail({
  filters,
  update,
  availableSectors,
}: {
  filters: Filters;
  update: (patch: Partial<Filters>, preset?: string | null) => void;
  availableSectors: string[];
}) {
  const toggleTag = (t: string) =>
    update({ tags: filters.tags.includes(t) ? filters.tags.filter((x) => x !== t) : [...filters.tags, t] });
  const toggleSector = (s: string) =>
    update({ sectors: filters.sectors.includes(s) ? filters.sectors.filter((x) => x !== s) : [...filters.sectors, s] });

  return (
    <aside className="w-full shrink-0 lg:w-64">
      <div className="flex flex-col gap-5 rounded-xl border border-border bg-card p-4">
        <div className="flex flex-col gap-2">
          <RailLabel>Insight tags</RailLabel>
          <div className="flex flex-wrap gap-1.5">
            {ALL_TAGS.map((t) => (
              <button
                key={t}
                onClick={() => toggleTag(t)}
                className={cn(
                  "rounded-full border px-2 py-0.5 text-[11px] font-medium transition-colors",
                  filters.tags.includes(t)
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border text-muted-foreground hover:text-foreground",
                )}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <RailLabel>Numeric filters</RailLabel>
          <NumInput label="RS rank ≤" value={filters.rankMax} onChange={(v) => update({ rankMax: v })} />
          <NumInput label="Trend score ≥" value={filters.trendMin} onChange={(v) => update({ trendMin: v })} />
          <NumInput label="Consistency ≥" value={filters.consMin} onChange={(v) => update({ consMin: v })} />
          <NumInput label="1M return ≥ %" value={filters.r1m} onChange={(v) => update({ r1m: v })} />
          <NumInput label="3M return ≥ %" value={filters.r3m} onChange={(v) => update({ r3m: v })} />
          <NumInput label="6M return ≥ %" value={filters.r6m} onChange={(v) => update({ r6m: v })} />
          <NumInput label="ATR % ≤" value={filters.atrMax} onChange={(v) => update({ atrMax: v })} />
          <NumInput label="Within % of 52w high" value={filters.nearHigh} onChange={(v) => update({ nearHigh: v })} />
          <NumInput label="Volume ratio ≥" value={filters.volMin} onChange={(v) => update({ volMin: v })} />
        </div>

        <div className="flex flex-col gap-2">
          <RailLabel>Trend position</RailLabel>
          <Toggle label="Above 50-DMA" on={filters.above50} onClick={() => update({ above50: !filters.above50 })} />
          <Toggle label="Above 200-DMA" on={filters.above200} onClick={() => update({ above200: !filters.above200 })} />
        </div>

        <div className="flex flex-col gap-2">
          <RailLabel>Sectors</RailLabel>
          <div className="flex max-h-56 flex-col gap-1 overflow-y-auto pr-1">
            {availableSectors.map((s) => (
              <label key={s} className="flex cursor-pointer items-center gap-2 text-[12px] text-muted-foreground hover:text-foreground">
                <input
                  type="checkbox"
                  checked={filters.sectors.includes(s)}
                  onChange={() => toggleSector(s)}
                  className="h-3.5 w-3.5"
                />
                {sectorLabel(s)}
              </label>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}

function RailLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
      {children}
    </span>
  );
}

function NumInput({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="flex items-center justify-between gap-2 text-[12px] text-muted-foreground">
      <span>{label}</span>
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-16 rounded-md border border-input bg-background px-2 py-1 text-right text-[12px] text-foreground"
      />
    </label>
  );
}

function Toggle({ label, on, onClick }: { label: string; on: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center justify-between rounded-md border px-2.5 py-1 text-[12px] transition-colors",
        on ? "border-primary bg-primary/10 text-foreground" : "border-border text-muted-foreground hover:text-foreground",
      )}
    >
      {label}
      <span className={cn("ml-2 h-2 w-2 rounded-full", on ? "bg-primary" : "bg-muted")} />
    </button>
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
