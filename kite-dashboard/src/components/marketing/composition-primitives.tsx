/* design_studies loop 28: the combined build menu from three reference
 * rounds (AEYE_STUDY, PERCEPT_STUDY, CLAY_STUDY part 2), B-a..B-i.
 * All geometry is DETERMINISTIC (no Math.random — RSC + hydration safe),
 * all figures/events are real (docs/portfolios.md, the 2026-05-12 signal
 * record), everything token-derived. Colour rule holds: colour arrives
 * through elements; panels stay white / soft / green-wash. */

import type { ReactNode } from "react";
import Link from "next/link";

/* ————— B-a · TexturePanel — generative card-media backdrops ————— */
/* The parked asset-study fields, re-homed at card scale (PERCEPT P2). */

const BAYER8 = [
  [0, 32, 8, 40, 2, 34, 10, 42],
  [48, 16, 56, 24, 50, 18, 58, 26],
  [12, 44, 4, 36, 14, 46, 6, 38],
  [60, 28, 52, 20, 62, 30, 54, 22],
  [3, 35, 11, 43, 1, 33, 9, 41],
  [51, 19, 59, 27, 49, 17, 57, 25],
  [15, 47, 7, 39, 13, 45, 5, 37],
  [63, 31, 55, 23, 61, 29, 53, 21],
];

function BayerPattern({
  id,
  density,
  cell,
}: {
  id: string;
  density: number;
  cell: number;
}) {
  const dots: string[] = [];
  const cut = density * 64;
  for (let y = 0; y < 8; y++)
    for (let x = 0; x < 8; x++)
      if ((BAYER8.at(y)?.at(x) ?? 64) < cut)
        dots.push(
          `M${x * cell + cell * 0.31} ${y * cell + cell * 0.31}m-${cell * 0.31} 0a${cell * 0.31} ${cell * 0.31} 0 1 0 ${cell * 0.62} 0a${cell * 0.31} ${cell * 0.31} 0 1 0 -${cell * 0.62} 0`,
        );
  return (
    <pattern
      id={id}
      width={cell * 8}
      height={cell * 8}
      patternUnits="userSpaceOnUse"
    >
      <path d={dots.join("")} fill="currentColor" />
    </pattern>
  );
}

export type TextureVariant = "dither" | "hatch" | "grid" | "dots";

export function TexturePanel({
  variant = "dither",
  className = "",
}: {
  variant?: TextureVariant;
  className?: string;
}) {
  const W = 640;
  const H = 420;
  const uid = `tx-${variant}`;
  let body: ReactNode = null;

  if (variant === "dither") {
    const bands = [0.5, 0.36, 0.24, 0.15, 0.08, 0.04, 0.015, 0];
    const bw = W / bands.length;
    body = (
      <>
        <defs>
          {bands.map((d, i) =>
            d > 0 ? (
              <BayerPattern key={i} id={`${uid}-${i}`} density={d} cell={5} />
            ) : null,
          )}
        </defs>
        <g className="text-acc1-line" opacity="0.5">
          {bands.map((d, i) =>
            d > 0 ? (
              <rect
                key={i}
                x={i * bw}
                y={0}
                width={bw + 1}
                height={H}
                fill={`url(#${uid}-${i})`}
              />
            ) : null,
          )}
        </g>
      </>
    );
  } else if (variant === "grid") {
    /* fine chart-paper: the homepage grid idiom at card scale */
    body = (
      <>
        <defs>
          <pattern
            id={`${uid}-p`}
            width={36}
            height={36}
            patternUnits="userSpaceOnUse"
          >
            <path
              d="M36 0H0V36"
              fill="none"
              stroke="currentColor"
              strokeWidth="1"
            />
          </pattern>
          <radialGradient id={`${uid}-f`} cx="0.6" cy="0.4" r="0.9">
            <stop offset="0" stopColor="#fff" stopOpacity="1" />
            <stop offset="1" stopColor="#fff" stopOpacity="0" />
          </radialGradient>
          <mask id={`${uid}-m`}>
            <rect width={W} height={H} fill={`url(#${uid}-f)`} />
          </mask>
        </defs>
        <rect
          width={W}
          height={H}
          fill={`url(#${uid}-p)`}
          mask={`url(#${uid}-m)`}
          className="text-acc1-line"
          opacity="0.4"
        />
      </>
    );
  } else if (variant === "dots") {
    /* uniform dot lattice — the pipeline canvas as a texture */
    body = (
      <>
        <defs>
          <pattern
            id={`${uid}-p`}
            width={20}
            height={20}
            patternUnits="userSpaceOnUse"
          >
            <circle cx={2} cy={2} r={1.4} fill="currentColor" />
          </pattern>
          <linearGradient id={`${uid}-f`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#fff" stopOpacity="0.25" />
            <stop offset="1" stopColor="#fff" stopOpacity="1" />
          </linearGradient>
          <mask id={`${uid}-m`}>
            <rect width={W} height={H} fill={`url(#${uid}-f)`} />
          </mask>
        </defs>
        <rect
          width={W}
          height={H}
          fill={`url(#${uid}-p)`}
          mask={`url(#${uid}-m)`}
          className="text-acc1-line"
          opacity="0.5"
        />
      </>
    );
  } else {
    /* hatch: fine diagonal strokes fading across, the quiet one */
    body = (
      <>
        <defs>
          <pattern
            id={`${uid}-p`}
            width={7}
            height={7}
            patternTransform="rotate(45)"
            patternUnits="userSpaceOnUse"
          >
            <line
              x1="0"
              y1="0"
              x2="0"
              y2="7"
              stroke="currentColor"
              strokeWidth="1"
            />
          </pattern>
          <linearGradient id={`${uid}-f`} x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="#fff" stopOpacity="0" />
            <stop offset="0.65" stopColor="#fff" stopOpacity="1" />
          </linearGradient>
          <mask id={`${uid}-m`}>
            <rect width={W} height={H} fill={`url(#${uid}-f)`} />
          </mask>
        </defs>
        <rect
          width={W}
          height={H}
          fill={`url(#${uid}-p)`}
          mask={`url(#${uid}-m)`}
          className="text-acc1-line"
          opacity="0.35"
        />
      </>
    );
  }

  return (
    <svg
      aria-hidden
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="xMidYMid slice"
      className={`pointer-events-none absolute inset-0 h-full w-full ${className}`}
    >
      {body}
    </svg>
  );
}

/* ————— B-d · SignalChips — real events as ambient rows ————— */
/* PERCEPT P4 × the aeye tape, with OUR real record: the 2026-05-12
 * Core Momentum ranks (data/final_portfolio/final_portfolio_24.csv)
 * and pipeline facts. No invented events. */

/* kind -> dot colour: portfolio events green (acc1), system/pipeline
 * events sky (acc3, the info accent). Structure, not decoration. */
export type SignalChip = {
  text: string;
  kind?: "portfolio" | "system";
  highlight?: boolean;
};

const REAL_CHIPS: SignalChip[][] = [
  [
    { text: "HFCL · rank 1 · score 4.78", highlight: true },
    { text: "HINDCOPPER · rank 2 · 3.74" },
    { text: "MCX · rank 3 · 3.64" },
    { text: "NATIONALUM · rank 4 · 3.60" },
    { text: "signals rebuilt · 16:30 IST", kind: "system" },
  ],
  [
    { text: "POWERINDIA · rank 5 · 3.08" },
    { text: "weekly rebalance published", kind: "system" },
    { text: "KIRLOSENG · rank 6 · 2.98" },
    { text: "NSE 500 scored · 499 names", kind: "system" },
    { text: "BSE · rank 7 · 2.91" },
  ],
];

export function SignalChips({
  rows = REAL_CHIPS,
  dark = false,
  className = "",
}: {
  rows?: SignalChip[][];
  dark?: boolean;
  className?: string;
}) {
  return (
    <div
      className={`space-y-3 overflow-hidden ${className}`}
      style={{
        maskImage:
          "linear-gradient(90deg, transparent, #000 12%, #000 88%, transparent)",
        WebkitMaskImage:
          "linear-gradient(90deg, transparent, #000 12%, #000 88%, transparent)",
      }}
    >
      {rows.map((row, ri) => (
        <div
          key={ri}
          className={`mw-chip-row flex w-max gap-3 ${ri % 2 ? "mw-chip-row-alt" : ""}`}
        >
          {row.map((c) =>
            c.highlight ? (
              <span
                key={c.text}
                className="flex items-center gap-2 rounded-full bg-card px-4 py-2 font-mono text-xs font-medium text-foreground shadow-[0_6px_18px_-8px_rgba(20,26,23,0.35)]"
              >
                <span className="h-2 w-2 rounded-full bg-primary" />
                {c.text}
              </span>
            ) : (
              <span
                key={c.text}
                className={`flex items-center gap-2 rounded-full border px-4 py-2 font-mono text-xs ${
                  dark
                    ? "border-[color-mix(in_oklab,var(--surface-panel-deep-foreground)_25%,transparent)] text-[color-mix(in_oklab,var(--surface-panel-deep-foreground)_75%,transparent)]"
                    : "border-border text-muted-foreground"
                }`}
              >
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    dark
                      ? "bg-[var(--surface-panel-deep-foreground)] opacity-60"
                      : c.kind === "system"
                        ? "bg-acc3-line"
                        : "bg-acc1-line"
                  }`}
                />
                {c.text}
              </span>
            ),
          )}
        </div>
      ))}
      <p
        className={`pt-1 font-mono text-[10.5px] ${dark ? "text-[color-mix(in_oklab,var(--surface-panel-deep-foreground)_55%,transparent)]" : "text-muted-foreground/80"}`}
      >
        real signal record · 12 may 2026
      </p>
    </div>
  );
}

/* ————— B-c · InkBand — the sustained dark movement ————— */
/* PERCEPT P3, on our green-deep drench token. One per page. */

export function InkBand({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`overflow-hidden rounded-[32px] bg-[var(--surface-panel-deep)] px-7 py-14 text-[var(--surface-panel-deep-foreground)] sm:px-12 sm:py-20 ${className}`}
    >
      {children}
    </section>
  );
}

export function InkCard({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="rounded-[16px] border border-[color-mix(in_oklab,var(--surface-panel-deep-foreground)_18%,transparent)] bg-[color-mix(in_oklab,var(--surface-panel-deep-foreground)_6%,transparent)] px-6 py-6">
      <h3 className="text-lg font-semibold text-[var(--surface-panel-deep-foreground)]">
        {title}
      </h3>
      <p className="mt-2 text-sm leading-[1.6] text-[color-mix(in_oklab,var(--surface-panel-deep-foreground)_72%,transparent)]">
        {children}
      </p>
    </div>
  );
}

/* ————— B-f · ProofMosaic — the record as a tile wall ————— */
/* Clay K3 without client logos: real stats, method facts, the
 * rejected ledger, and real library titles in ONE cell language. */

type MosaicCell =
  | { kind: "stat"; value: string; label: string }
  | { kind: "method"; text: string }
  | { kind: "reject"; text: string }
  | { kind: "library"; text: string };

const MOSAIC_ROWS: MosaicCell[][] = [
  [
    { kind: "stat", value: "44.78%", label: "CAGR · OOS 2017–26" },
    { kind: "method", text: "20% drawdown stop · weekly" },
    { kind: "reject", text: "volatility targeting" },
    { kind: "stat", value: "1.86", label: "Sharpe · net of slippage" },
    { kind: "library", text: "What Marketworks is, and how to use it" },
    { kind: "method", text: "equal weight 1/N · 7.5% cap" },
  ],
  [
    { kind: "method", text: "rebuilt daily · 16:30 IST" },
    { kind: "stat", value: "−36.6%", label: "max drawdown · shown" },
    { kind: "reject", text: "longer lookbacks (9, 12m)" },
    { kind: "library", text: "A weak rupee is a slow tax on imports" },
    { kind: "stat", value: "9.3y", label: "validation window" },
    { kind: "reject", text: "volume-weighted scoring" },
  ],
];

function MosaicTile({ cell }: { cell: MosaicCell }) {
  if (cell.kind === "stat")
    return (
      <div className="flex min-w-[190px] flex-col justify-center rounded-[14px] border border-border bg-card px-5 py-4">
        <span className="font-mono text-xl text-foreground [font-variant-numeric:tabular-nums]">
          {cell.value}
        </span>
        <span className="mt-1 text-xs text-muted-foreground">{cell.label}</span>
      </div>
    );
  if (cell.kind === "method")
    return (
      <div className="flex min-w-[180px] items-center rounded-[14px] bg-acc2-bg px-5 py-4 font-mono text-xs text-acc2-fg">
        {cell.text}
      </div>
    );
  if (cell.kind === "reject")
    return (
      <div className="flex min-w-[180px] items-center gap-2 rounded-[14px] border border-dashed border-border px-5 py-4 font-mono text-xs text-muted-foreground">
        <span className="text-[10px] uppercase tracking-[0.08em] text-acc4-fg">
          rejected
        </span>
        <span className="line-through decoration-[1.5px]">{cell.text}</span>
      </div>
    );
  return (
    <div className="flex min-w-[220px] max-w-[260px] items-center rounded-[14px] border border-border bg-background px-5 py-4 text-[13px] leading-snug text-foreground">
      <span>
        <span className="mr-2 font-mono text-[10px] uppercase text-acc5-fg">
          /library
        </span>
        {cell.text}
      </span>
    </div>
  );
}

export function ProofMosaic({ className = "" }: { className?: string }) {
  return (
    <div
      className={`overflow-hidden rounded-[24px] border border-border/60 bg-surface-panel-mist px-2 py-8 ${className}`}
      style={{
        maskImage:
          "linear-gradient(90deg, transparent, #000 7%, #000 93%, transparent)",
        WebkitMaskImage:
          "linear-gradient(90deg, transparent, #000 7%, #000 93%, transparent)",
      }}
    >
      {MOSAIC_ROWS.map((row, ri) => (
        <div
          key={ri}
          className={`mw-chip-row mt-3 flex w-max gap-3 first:mt-0 ${ri % 2 ? "mw-chip-row-alt" : ""}`}
        >
          {row.map((c, i) => (
            <MosaicTile key={i} cell={c} />
          ))}
        </div>
      ))}
    </div>
  );
}

/* ————— B-i · SignalBoard — the real table as hero media ————— */
/* Clay K4: a real product table with a highlighted row under a
 * portfolio pill row. Data: the 2026-05-12 signal record. */

const BOARD_ROWS = [
  { rank: 1, symbol: "HFCL", score: 4.78, hot: true },
  { rank: 2, symbol: "HINDCOPPER", score: 3.74 },
  { rank: 3, symbol: "MCX", score: 3.64 },
  { rank: 4, symbol: "NATIONALUM", score: 3.6 },
  { rank: 5, symbol: "POWERINDIA", score: 3.08 },
  { rank: 6, symbol: "KIRLOSENG", score: 2.98 },
];

export function SignalBoard({ className = "" }: { className?: string }) {
  const max = BOARD_ROWS[0]!.score;
  return (
    <div className={className}>
      {/* portfolio identity hues (proposal): Core=green, Quality=sun,
          Trend=sky, Defensive=purple — the same hue follows each
          portfolio everywhere it appears. */}
      <div className="mb-4 flex flex-wrap gap-2" aria-hidden>
        <span className="rounded-full bg-primary px-4 py-1.5 text-xs font-semibold text-primary-foreground">
          Core Momentum
        </span>
        <span className="rounded-full bg-acc2-bg px-4 py-1.5 text-xs font-semibold text-acc2-fg">
          Quality Momentum
        </span>
        <span className="rounded-full bg-acc3-bg px-4 py-1.5 text-xs font-semibold text-acc3-fg">
          Trend Leaders
        </span>
        <span className="rounded-full bg-acc5-bg px-4 py-1.5 text-xs font-semibold text-acc5-fg">
          Defensive Blend
        </span>
      </div>
      <div className="overflow-hidden rounded-[16px] border border-border bg-card">
        <div className="flex items-center justify-between border-b border-border px-5 py-3">
          <p className="text-sm font-semibold text-foreground">
            Signal board · NSE 500
          </p>
          <p className="font-mono text-[11px] text-acc1-fg">
            12 MAY 2026 · 16:30 IST
          </p>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border font-mono text-[10.5px] uppercase tracking-[0.08em] text-muted-foreground">
              <th className="w-14 px-5 py-2.5 text-left font-medium">#</th>
              <th className="px-2 py-2.5 text-left font-medium">Symbol</th>
              <th className="px-2 py-2.5 text-left font-medium">Momentum</th>
              <th className="w-20 px-5 py-2.5 text-right font-medium">Score</th>
            </tr>
          </thead>
          <tbody>
            {BOARD_ROWS.map((r) => (
              <tr
                key={r.symbol}
                className={`border-b border-border/60 last:border-0 ${r.hot ? "bg-acc1-bg" : ""}`}
              >
                <td className="px-5 py-2.5 font-mono text-xs text-muted-foreground">
                  {r.rank}
                </td>
                <td className="px-2 py-2.5 font-semibold text-foreground">
                  {r.symbol}
                </td>
                <td className="px-2 py-2.5">
                  <span className="block h-1.5 max-w-[180px] rounded-full bg-acc1-bg">
                    <span
                      className="block h-1.5 rounded-full bg-primary"
                      style={{ width: `${(r.score / max) * 100}%` }}
                    />
                  </span>
                </td>
                <td className="px-5 py-2.5 text-right font-mono text-xs text-foreground [font-variant-numeric:tabular-nums]">
                  {r.score.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 font-mono text-[11px] text-muted-foreground">
        real ranks from the research record · pills illustrative until wired
      </p>
    </div>
  );
}

/* ————— B-e · StackSections — clay K1, colour-rule-resolved ————— */
/* Pure-CSS sticky stack: each panel pins at the top and the next
 * slides over it. Panels stay white / soft / green-wash; the triads
 * live in elements inside (the loop-23 rule). */

export function StackSection({
  tone = "card",
  children,
  className = "",
}: {
  tone?: "card" | "soft" | "wash";
  children: ReactNode;
  className?: string;
}) {
  const bg =
    tone === "wash"
      ? "bg-[var(--wash1)]"
      : tone === "soft"
        ? "bg-surface-panel-mist"
        : "bg-card";
  return (
    <section
      className={`sticky top-16 min-h-[68vh] rounded-t-[36px] border border-border/70 ${bg} px-7 py-12 shadow-[0_-14px_40px_-24px_rgba(20,26,23,0.25)] sm:px-12 ${className}`}
    >
      {children}
    </section>
  );
}

/* ————— B-b · TexturedFooter — the merged CTA + footer ————— */
/* PERCEPT P8 on our green-deep: one continuous textured surface
 * carrying the CTA, the sitemap, and the giant lowercase wordmark. */

const FOOTER_COLS: { head: string; links: [string, string][] }[] = [
  {
    head: "Product",
    links: [
      ["Portfolios", "/portfolios"],
      ["Library", "/library"],
      ["Insights", "/insights"],
    ],
  },
  {
    head: "Company",
    links: [
      ["Terms", "/terms"],
      ["Privacy", "/privacy"],
      ["Disclaimer", "/disclaimer"],
    ],
  },
];

export function TexturedFooter({ className = "" }: { className?: string }) {
  return (
    <footer
      className={`relative overflow-hidden rounded-[32px] bg-[var(--surface-panel-deep)] text-[var(--surface-panel-deep-foreground)] ${className}`}
    >
      {/* the texture: fine hatch fading in from the right, pale ink */}
      <svg
        aria-hidden
        className="pointer-events-none absolute inset-0 h-full w-full opacity-[0.14]"
        preserveAspectRatio="xMidYMid slice"
        viewBox="0 0 1200 700"
      >
        <defs>
          <pattern
            id="tf-hatch"
            width="6"
            height="6"
            patternTransform="rotate(45)"
            patternUnits="userSpaceOnUse"
          >
            <line x1="0" y1="0" x2="0" y2="6" stroke="currentColor" strokeWidth="1" />
          </pattern>
          <radialGradient id="tf-fade" cx="0.85" cy="0.15" r="1">
            <stop offset="0" stopColor="#fff" stopOpacity="1" />
            <stop offset="0.7" stopColor="#fff" stopOpacity="0" />
          </radialGradient>
          <mask id="tf-mask">
            <rect width="1200" height="700" fill="url(#tf-fade)" />
          </mask>
        </defs>
        <rect
          width="1200"
          height="700"
          fill="url(#tf-hatch)"
          mask="url(#tf-mask)"
        />
      </svg>

      <div className="relative px-7 pb-8 pt-16 sm:px-12 sm:pt-20">
        <div className="flex flex-wrap items-end justify-between gap-8">
          <h2 className="max-w-[16ch] text-3xl font-semibold leading-[1.15] sm:text-4xl">
            Follow the market&apos;s leaders, calmly.
          </h2>
          <Link
            href="/sign-up"
            className="rounded-full bg-[var(--surface-panel-deep-foreground)] px-6 py-3 text-sm font-semibold text-[var(--surface-panel-deep)]"
          >
            Get beta access
          </Link>
        </div>

        <div className="mt-12 grid gap-10 border-t border-[color-mix(in_oklab,var(--surface-panel-deep-foreground)_20%,transparent)] pt-10 sm:grid-cols-[1fr_auto_auto] sm:gap-20">
          <p className="max-w-[38ch] text-sm leading-[1.65] text-[color-mix(in_oklab,var(--surface-panel-deep-foreground)_70%,transparent)]">
            Marketworks publishes educational research grounded in our own
            momentum portfolios and live insight engine. Markets carry risk;
            past behaviour is not a guarantee of future results.
          </p>
          {FOOTER_COLS.map((col) => (
            <div key={col.head}>
              <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-[color-mix(in_oklab,var(--surface-panel-deep-foreground)_55%,transparent)]">
                {col.head}
              </p>
              <ul className="mt-4 space-y-2.5 text-sm font-medium">
                {col.links.map(([label, href]) => (
                  <li key={label}>
                    <Link href={href} className="hover:underline">
                      {label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <p
          aria-hidden
          className="mt-14 select-none text-center text-[clamp(64px,13vw,160px)] font-semibold leading-none tracking-[-0.04em] text-[color-mix(in_oklab,var(--surface-panel-deep-foreground)_16%,transparent)]"
        >
          marketworks
        </p>

        <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-[color-mix(in_oklab,var(--surface-panel-deep-foreground)_16%,transparent)] pt-5 font-mono text-[11px] text-[color-mix(in_oklab,var(--surface-panel-deep-foreground)_55%,transparent)]">
          <span>© 2026 Marketworks Research</span>
          <a href="#top" className="hover:underline">
            back to top ↑
          </a>
        </div>
      </div>
    </footer>
  );
}
