import { cn } from "@/lib/utils";
import {
  fmtPct,
  regimeLabel,
  type RegimeSnapshot,
  type SectorRSSnapshot,
} from "@/lib/insights-api";

/** Tone → text color, using the brand role tokens + semantic finance colors
 *  provided by the `.mw-app` scope. */
export type Tone = "default" | "positive" | "negative" | "warning" | "muted";

const TONE_TEXT = new Map<Tone, string>([
  ["default", "text-foreground"],
  ["positive", "text-[color:var(--positive)]"],
  ["negative", "text-[color:var(--negative)]"],
  ["warning", "text-[color:var(--warning)]"],
  ["muted", "text-muted-foreground"],
]);

function toneClass(tone: Tone): string {
  return TONE_TEXT.get(tone) ?? "text-foreground";
}

export function Eyebrow({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground",
        className,
      )}
    >
      {children}
    </span>
  );
}

/** A page section with a Fraunces heading and optional right-aligned help. */
export function Section({
  title,
  help,
  children,
}: {
  title: string;
  help?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-baseline justify-between gap-4">
        <h3 className="text-xl font-semibold tracking-[-0.01em] text-foreground">
          {title}
        </h3>
        {help && <div className="flex shrink-0 gap-3 text-[13px]">{help}</div>}
      </div>
      {children}
    </section>
  );
}

/** The bottom "so what" line on a headline card — a plain-English takeaway of
 *  what the current reading means. Descriptive only, never a call to act. */
export function CardTakeaway({ children }: { children: React.ReactNode }) {
  return (
    <p className="mt-auto border-t border-border pt-3 text-[13px] leading-[1.5] text-foreground">
      {children}
    </p>
  );
}

/** A stat card: small label, large value (tone-colored), sub-line + help, and
 *  an optional bottom takeaway. */
export function MetricCard({
  label,
  value,
  sub,
  tone = "default",
  help,
  takeaway,
}: {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  tone?: Tone;
  help?: React.ReactNode;
  takeaway?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5 rounded-xl border border-border bg-card p-5">
      <Eyebrow>{label}</Eyebrow>
      <span className={cn("text-3xl font-semibold leading-tight", toneClass(tone))}>
        {value}
      </span>
      {sub && <span className="text-[13px] leading-snug text-muted-foreground">{sub}</span>}
      {help && <div className="mt-1">{help}</div>}
      {takeaway && <CardTakeaway>{takeaway}</CardTakeaway>}
    </div>
  );
}

/** Semantic-coloured percentage (green up / red down). `v` is a ratio. */
export function Pct({
  v,
  decimals = 1,
  signed = true,
}: {
  v: number | null | undefined;
  decimals?: number;
  signed?: boolean;
}) {
  if (v === null || v === undefined || Number.isNaN(v)) {
    return <span className="text-muted-foreground">—</span>;
  }
  const tone: Tone = v > 0 ? "positive" : v < 0 ? "negative" : "muted";
  return <span className={toneClass(tone)}>{fmtPct(v, decimals, signed)}</span>;
}

const REGIME_TONE = new Map<RegimeSnapshot["regime"], Tone>([
  ["TREND_BULL", "positive"],
  ["DRIFT", "muted"],
  ["STRETCHED", "warning"],
  ["STRESS", "negative"],
]);

// Plain-English "so what" per regime. Descriptive of conditions — no
// buy/sell call, no forecast.
const REGIME_TAKEAWAY = new Map<RegimeSnapshot["regime"], string>([
  ["TREND_BULL", "The market is trending up and most stocks are joining in — conditions are healthy."],
  ["DRIFT", "No strong trend right now — the market is drifting sideways on mixed signals."],
  ["STRETCHED", "The market is running hot and almost everyone's optimistic — historically a time to be a little more careful, not a sell signal."],
  ["STRESS", "The market is under pressure — either fear is up or fewer stocks are holding their trend."],
]);

export function RegimeCard({
  regime,
  help,
}: {
  regime: RegimeSnapshot;
  help?: React.ReactNode;
}) {
  const transitioned =
    regime.prev_regime && regime.persistence_days <= 10
      ? `from ${regimeLabel(regime.prev_regime)} · day ${regime.persistence_days}`
      : `Day ${regime.persistence_days}`;
  return (
    <MetricCard
      label="Regime"
      value={regimeLabel(regime.regime)}
      tone={REGIME_TONE.get(regime.regime) ?? "default"}
      sub={transitioned}
      help={help}
      takeaway={REGIME_TAKEAWAY.get(regime.regime)}
    />
  );
}

/** A small pill for an insight tag or band label. Render only engine label
 *  strings verbatim (compliance surface — see kite-api/app/insights/scores.py).
 *  `tone` is deliberately restrained: bands/tags describe a state, they never
 *  imply a buy/sell action or a mean-reversion call. */
export function Tag({ label, tone = "muted" }: { label: string; tone?: Tone }) {
  const border =
    tone === "positive"
      ? "border-[color:var(--positive)] text-[color:var(--positive)]"
      : tone === "warning"
        ? "border-[color:var(--warning)] text-[color:var(--warning)]"
        : "border-border text-muted-foreground";
  return (
    <span className={cn("inline-block rounded-full border px-2 py-0.5 text-[11px] font-medium", border)}>
      {label}
    </span>
  );
}

/** Volume-confirmation band → tone. "Strong" reads positive (participation
 *  confirmed); the rest stay neutral. */
export function volumeBandTone(band: string | null): Tone {
  return band === "Strong" ? "positive" : "muted";
}

/** Shared tone → badge border/text classes (used by the tag icon badges). */
export function badgeToneClass(tone: Tone): string {
  return tone === "positive"
    ? "border-[color:var(--positive)] text-[color:var(--positive)]"
    : tone === "warning"
      ? "border-[color:var(--warning)] text-[color:var(--warning)]"
      : "border-border text-muted-foreground";
}

/** A 0–100 score rendered as a value + thin bar. `tone` colors the bar; for
 *  extension risk pass "muted" — a high reading is descriptive ("stretched vs
 *  its own history"), NOT a signal to act, so it must not read as a red alert. */
export function ScoreBar({
  value,
  tone = "default",
  suffix,
}: {
  value: number | null;
  tone?: Tone;
  suffix?: string;
}) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return <span className="text-muted-foreground">—</span>;
  }
  const pct = Math.max(0, Math.min(100, value));
  const color =
    tone === "positive"
      ? "var(--positive)"
      : tone === "warning"
        ? "var(--warning)"
        : tone === "negative"
          ? "var(--negative)"
          : "var(--muted-foreground)";
  return (
    <div className="flex items-center gap-2">
      <span className="w-9 shrink-0 text-right font-mono text-[13px] tabular-nums text-foreground">
        {pct.toFixed(0)}
      </span>
      <div className="h-1.5 w-full min-w-[40px] overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      {suffix && <span className="shrink-0 text-[11px] text-muted-foreground">{suffix}</span>}
    </div>
  );
}

/** Ranked sector RS leaderboard as a diverging ("tornado") chart: the sector
 *  name sits on the centre zero-axis, outperformers (green) extend right and
 *  laggards (red) extend left, each with its % riding the bar's outer tip.
 *  `rs_60d` is a ratio (vs Nifty 50). */
export function SectorBars({
  sectors,
  limit = 12,
}: {
  sectors: SectorRSSnapshot[];
  limit?: number;
}) {
  const rows = sectors
    .filter((s) => s.rs_60d !== null)
    .slice(0, limit);
  const maxAbs = Math.max(
    1e-9,
    ...rows.map((s) => Math.abs(s.rs_60d ?? 0)),
  );

  return (
    <div className="flex flex-col gap-2">
      {rows.map((s) => {
        const v = s.rs_60d ?? 0;
        const positive = v >= 0;
        // Cap at 80% of each half so the % label at the tip never overflows.
        const width = `${Math.max(4, (Math.abs(v) / maxAbs) * 80)}%`;
        const color = positive ? "var(--positive)" : "var(--negative)";
        return (
          <div
            key={s.sector}
            className="grid items-center gap-2"
            style={{ gridTemplateColumns: "1fr 132px 1fr" }}
          >
            {/* Left half — laggards (red), bar grows toward centre */}
            <div className="flex items-center justify-end gap-2">
              {!positive && (
                <>
                  <span className="font-mono text-[13px] tabular-nums">
                    <Pct v={v} />
                  </span>
                  <div
                    className="h-6 rounded-[4px]"
                    style={{ width, backgroundColor: color }}
                  />
                </>
              )}
            </div>

            {/* Centre — sector name on the zero-axis */}
            <span className="truncate text-center font-mono text-[13px] uppercase tracking-[0.04em] text-foreground">
              {s.sector.replace("NIFTY_", "")}
            </span>

            {/* Right half — leaders (green), bar grows outward from centre */}
            <div className="flex items-center gap-2">
              {positive && (
                <>
                  <div
                    className="h-6 rounded-[4px]"
                    style={{ width, backgroundColor: color }}
                  />
                  <span className="font-mono text-[13px] tabular-nums">
                    <Pct v={v} />
                  </span>
                </>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
