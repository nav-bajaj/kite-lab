import Link from "next/link";
import {
  getStockDetail,
  type StockRow,
} from "@/lib/insights-api";
import {
  fmtPct,
  fmtNum,
  sectorLabel,
} from "@/lib/insights-format";
import { Pct, Tag, ScoreBar, volumeBandTone, type Tone } from "@/components/insights/ui";
import { PriceChart, RSSparkline } from "./_chart";

export const dynamic = "force-dynamic";
export const revalidate = 900;

interface PageProps {
  params: Promise<{ symbol: string }>;
  searchParams: Promise<{ date?: string }>;
}

export async function generateMetadata({ params }: PageProps) {
  const { symbol } = await params;
  return {
    title: `${symbol} — Marketworks Insights`,
    description: `Relative strength, trend, extension and volume read for ${symbol}. Educational, not a recommendation.`,
  };
}

function LearnLink({ slug }: { slug: string }) {
  return (
    <Link
      href={`/insights/learn/${slug}`}
      title="What is this?"
      className="text-[11px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
    >
      What is this?
    </Link>
  );
}

export default async function StockDetailPage({ params, searchParams }: PageProps) {
  const { symbol } = await params;
  const { date } = await searchParams;
  const backHref = `/insights/screener${date ? `?date=${encodeURIComponent(date)}` : ""}`;

  let detail;
  try {
    detail = await getStockDetail(symbol, date);
  } catch {
    return <NotFoundState symbol={symbol} backHref={backHref} />;
  }
  if (!detail.data_available || !detail.row) {
    return <NotFoundState symbol={symbol} backHref={backHref} />;
  }

  const r = detail.row;
  const peerQuery = date ? `?date=${encodeURIComponent(date)}` : "";
  const isLeader = r.tags.includes("Momentum leader");

  return (
    <main className="flex flex-col gap-10">
      <Link href={backHref} className="text-[13px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline">
        ← Back to screener
      </Link>

      {/* Header */}
      <section className="flex flex-col gap-3">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="flex flex-col gap-1">
            <h2 className="font-serif text-3xl font-medium tracking-[-0.01em] text-foreground">{r.symbol}</h2>
            <p className="text-[13px] text-muted-foreground">
              {r.zerodha_sector ? (
                <span className="font-medium text-foreground">{r.zerodha_sector}</span>
              ) : r.sectors.length ? (
                r.sectors.map(sectorLabel).join(" · ")
              ) : (
                "Sector not classified"
              )}
              {r.super_sector && r.super_sector !== r.zerodha_sector ? ` · ${r.super_sector}` : ""}
              {r.zerodha_sector && r.sectors.length ? ` · ${r.sectors.map(sectorLabel).join(" · ")}` : ""}
              {detail.asof && ` · as of ${new Date(detail.asof).toLocaleDateString("en-IN")}`}
            </p>
          </div>
          <div className="text-right">
            <div className="font-mono text-2xl text-foreground">{fmtNum(r.close, 2)}</div>
            <div className="text-sm"><Pct v={r.ret_1d} decimals={2} /> today</div>
          </div>
        </div>
        {r.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {r.tags.map((t) => <Tag key={t} label={t} />)}
          </div>
        )}
        {isLeader && (
          <div
            className="max-w-2xl rounded-lg border border-[color:var(--positive)] bg-[color:var(--positive)]/5 px-3 py-2 text-[12px] leading-[1.5] text-muted-foreground"
            title="Validity-tested against a matched NSE 500 baseline over 165 sample dates"
          >
            <span className="mr-1 font-medium text-[color:var(--positive)]">Validity-tested ✓</span>
            RS top-decile names historically led a matched NSE 500 baseline by
            +1.19pp over the next 20 trading days (56% positive vs 54% baseline;
            +3.9pp at 60d), across our 16-year sample. Historical tendency, not a
            forecast for this stock.
          </div>
        )}
      </section>

      {/* Score row */}
      <section className="flex flex-col gap-4">
        <SectionHead title="Scores" />
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-5">
          <ScoreCard
            label="RS rank"
            learn="rs-rank"
            value={r.rank === null ? "—" : `#${r.rank}`}
            sub={
              r.sector_rank && r.sector_size
                ? `#${r.sector_rank} of ${r.sector_size} in sector`
                : r.percentile !== null
                  ? `${r.percentile.toFixed(0)}th percentile`
                  : undefined
            }
          />
          <ScoreCard label="Trend" learn="trend-score" bar={r.trend_score} barTone="positive" />
          <ScoreCard
            label="Extension"
            learn="extension-risk"
            value={r.extension_band ?? "—"}
            sub="stretched vs own history"
          />
          <ScoreCard
            label="Volume confirmation"
            learn="volume-confirmation"
            value={r.volume_band ?? "—"}
            valueTone={volumeBandTone(r.volume_band)}
          />
          <ScoreCard label="Consistency" learn="momentum-consistency" bar={r.momentum_consistency} barTone="positive" />
        </div>
      </section>

      {/* Price chart */}
      <section className="flex flex-col gap-4">
        <SectionHead title="Price & moving averages" help={<span className="text-[12px] text-muted-foreground">1-year daily close with 50 / 200-DMA</span>} />
        <div className="rounded-xl border border-border bg-card p-4">
          <PriceChart series={detail.series} />
        </div>
      </section>

      <div className="grid grid-cols-1 gap-10 lg:grid-cols-2">
        {/* Trend structure */}
        <section className="flex flex-col gap-4">
          <SectionHead title="Trend structure" />
          <DataTable
            rows={[
              ["Above 20-DMA", boolText(r.above_20dma), fmtPct(r.dist_20dma_pct, 1, true)],
              ["Above 50-DMA", boolText(r.above_50dma), fmtPct(r.dist_50dma_pct, 1, true)],
              ["Above 100-DMA", boolText(r.above_100dma), fmtPct(r.dist_100dma_pct, 1, true)],
              ["Above 200-DMA", boolText(r.above_200dma), fmtPct(r.dist_200dma_pct, 1, true)],
              ["50-DMA > 200-DMA", boolText(r.dma_50_above_200), "—"],
              ["From 52w high", "—", fmtPct(r.dist_52w_high_pct, 1, true)],
              ["From 52w low", "—", fmtPct(r.dist_52w_low_pct, 1, true)],
              ["Days since 52w high", r.days_since_52w_high === null || r.days_since_52w_high === undefined ? "—" : String(r.days_since_52w_high), "—"],
            ]}
            headers={["", "", "Distance"]}
          />
        </section>

        {/* Momentum profile */}
        <section className="flex flex-col gap-4">
          <SectionHead title="Momentum profile" help={<LearnLink slug="rs-rank" />} />
          <ReturnLadder r={r} />
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              RS-rank history (monthly)
            </p>
            <RSSparkline history={detail.rs_rank_history} />
          </div>
        </section>

        {/* Volume profile */}
        <section className="flex flex-col gap-4">
          <SectionHead title="Volume profile" help={<LearnLink slug="volume-confirmation" />} />
          <DataTable
            rows={[
              ["Volume vs 20d avg", r.vol_ratio === null ? "—" : `${r.vol_ratio.toFixed(2)}x`, ""],
              ["5-day avg ratio", r.vol_ratio_5d === undefined || r.vol_ratio_5d === null ? "—" : `${r.vol_ratio_5d.toFixed(2)}x`, ""],
              ["Up/down vol (20d)", r.updown_vol_ratio_20d === undefined || r.updown_vol_ratio_20d === null ? "—" : `${r.updown_vol_ratio_20d.toFixed(2)}x`, ""],
              ["Avg turnover (20d)", r.avg_turnover_20d_cr === null ? "—" : `₹${fmtNum(r.avg_turnover_20d_cr, 1)} Cr`, ""],
              ["Liquidity tier", r.liquidity_tier ?? "—", ""],
            ]}
          />
        </section>

        {/* Risk profile */}
        <section className="flex flex-col gap-4">
          <SectionHead title="Risk profile" />
          <DataTable
            rows={[
              ["ATR %", r.atr_pct === null ? "—" : `${(r.atr_pct * 100).toFixed(1)}%`, ""],
              ["Realized vol 60d", r.vol_60d_annualized === null ? "—" : `${(r.vol_60d_annualized * 100).toFixed(0)}%`, ""],
              ["Vol percentile (1y)", r.vol_percentile_1y === null ? "—" : `${(r.vol_percentile_1y * 100).toFixed(0)}th`, ""],
              ["Beta (60d, Nifty 50)", fmtNum(r.beta_60d, 2), ""],
              ["Max drawdown 1y", fmtPct(r.max_drawdown_1y_pct, 1, true), ""],
              ["Drawdown from peak", fmtPct(r.drawdown_from_peak_pct, 1, true), ""],
            ]}
          />
        </section>
      </div>

      {/* Peers */}
      {detail.peers.length > 0 && (
        <section className="flex flex-col gap-3">
          <SectionHead title="Sector peers by RS" />
          <div className="flex flex-wrap gap-2">
            {detail.peers.map((p) => (
              <Link
                key={p.symbol}
                href={`/insights/stocks/${p.symbol}${peerQuery}`}
                className="rounded-lg border border-border bg-card px-3 py-2 text-[13px] transition-colors hover:bg-muted"
              >
                <span className="font-medium text-foreground">{p.symbol}</span>
                <span className="ml-2 text-muted-foreground">RS #{p.rank}</span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}

// ─────────────────────────── sub-components ───────────────────────────

function SectionHead({ title, help }: { title: string; help?: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-border pb-2">
      <h3 className="font-serif text-lg font-medium tracking-[-0.01em] text-foreground">{title}</h3>
      {help}
    </div>
  );
}

function ScoreCard({
  label,
  learn,
  value,
  sub,
  bar,
  barTone,
  valueTone,
}: {
  label: string;
  learn: string;
  value?: React.ReactNode;
  sub?: string;
  bar?: number | null;
  barTone?: Tone;
  valueTone?: Tone;
}) {
  const toneClass =
    valueTone === "positive" ? "text-[color:var(--positive)]" : "text-foreground";
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-border bg-card p-4">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{label}</span>
        <Link href={`/insights/learn/${learn}`} title="What is this?" className="text-[11px] text-muted-foreground hover:text-foreground">ⓘ</Link>
      </div>
      {bar !== undefined ? (
        <ScoreBar value={bar ?? null} tone={barTone ?? "default"} />
      ) : (
        <span className={`text-xl font-semibold ${toneClass}`}>{value}</span>
      )}
      {sub && <span className="text-[12px] text-muted-foreground">{sub}</span>}
    </div>
  );
}

function ReturnLadder({ r }: { r: StockRow }) {
  const items: [string, number | null][] = [
    ["1D", r.ret_1d],
    ["1W", r.ret_1w],
    ["1M", r.ret_1m],
    ["3M", r.ret_3m],
    ["6M", r.ret_6m],
    ["12M", r.ret_12m],
  ];
  return (
    <div className="grid grid-cols-6 gap-2 rounded-xl border border-border bg-card p-4">
      {items.map(([label, v]) => (
        <div key={label} className="flex flex-col items-center gap-1">
          <span className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</span>
          <span className="text-[13px]"><Pct v={v} decimals={1} /></span>
        </div>
      ))}
    </div>
  );
}

function DataTable({ rows, headers }: { rows: [string, string, string][] | [string, string][]; headers?: string[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-card">
      <table className="w-full text-[13px]">
        {headers && (
          <thead className="border-b border-border text-left text-muted-foreground">
            <tr>{headers.map((h, i) => <th key={i} className={`px-4 py-2 font-medium ${i > 0 ? "text-right" : ""}`}>{h}</th>)}</tr>
          </thead>
        )}
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-border last:border-0">
              {row.map((cell, j) => (
                <td key={j} className={`px-4 py-2 tabular-nums ${j === 0 ? "text-muted-foreground" : "text-right text-foreground"}`}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function boolText(v: boolean | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return v ? "Yes" : "No";
}

function NotFoundState({ symbol, backHref }: { symbol: string; backHref: string }) {
  return (
    <main className="flex flex-col gap-4">
      <h2 className="font-serif text-2xl font-medium tracking-[-0.01em] text-foreground">
        {symbol} not found
      </h2>
      <p className="max-w-2xl text-[14px] leading-[1.6] text-muted-foreground">
        We don&apos;t have stock-level data for <span className="font-medium text-foreground">{symbol}</span>. The
        screener covers the NSE 500 universe; check the spelling, or browse the
        full list from the screener.
      </p>
      <Link href={backHref} className="text-[13px] text-primary underline-offset-2 hover:underline">
        ← Back to screener
      </Link>
    </main>
  );
}
