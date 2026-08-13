/* design_studies loop 27: instrument primitives from AEYE_STUDY.md —
 * layout/motion devices only; colour and type come from the set system.
 * SectionMeter (D4) · StatTable (D5) · PipelineDiagram (D10) ·
 * ExhibitFrame (D8) · ScrambleIn (D3, rationed to one moment per page). */

import type { ReactNode } from "react";

import { ScrambleIn } from "./scramble-in";

export { ScrambleIn };

/* ————— SectionMeter — the metered index header ————— */

export function SectionMeter({
  index,
  total,
  label,
  accentClassName = "text-acc1-fg",
  className = "",
}: {
  index: number;
  total: number;
  label: string;
  /* rotate per section when sections form a sibling set (the loop-23
   * accent rule: rotation encodes structure) — e.g. text-acc2-fg */
  accentClassName?: string;
  className?: string;
}) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    <div
      className={`flex items-baseline gap-4 font-mono text-xs tracking-[0.04em] ${className}`}
    >
      <span className="shrink-0 text-foreground">
        [{pad(index)}/<span className="text-muted-foreground">{pad(total)}</span>]
      </span>
      <span aria-hidden className="w-6 border-t border-border self-center" />
      <span className="shrink-0 uppercase text-muted-foreground">
        <span aria-hidden className={accentClassName}>&gt; </span>
        {label}
      </span>
      <span aria-hidden className="flex-1 border-t border-border self-center" />
    </div>
  );
}

/* ————— StatTable — figures in hairline cells, no cards ————— */

export type StatCell = { value: string; label: string; note?: string };

export function StatTable({
  cells,
  footnote,
  className = "",
}: {
  cells: StatCell[];
  footnote?: string;
  className?: string;
}) {
  return (
    <div className={className}>
      <div
        className="grid gap-px overflow-hidden rounded-[14px] border border-border bg-border sm:grid-flow-col sm:auto-cols-fr"
      >
        {cells.map((c) => (
          <div key={c.label} className="bg-card px-6 py-6">
            <p className="font-mono text-[26px] leading-none tracking-[-0.01em] text-foreground [font-variant-numeric:tabular-nums]">
              {c.value}
            </p>
            <p className="mt-2.5 text-[13px] font-medium text-muted-foreground">
              {c.label}
            </p>
            {c.note ? (
              <p className="mt-1 text-xs leading-[1.5] text-muted-foreground/80">
                {c.note}
              </p>
            ) : null}
          </div>
        ))}
      </div>
      {footnote ? (
        <p className="mt-3 font-mono text-[11px] leading-[1.6] text-muted-foreground">
          {footnote}
        </p>
      ) : null}
    </div>
  );
}

/* ————— PipelineDiagram — the real daily pipeline as nodes ————— */

const PIPELINE_STEPS = [
  { id: "LOGIN", sub: "kite session" },
  { id: "FETCH", sub: "nse 500 + indices" },
  { id: "ADJUST", sub: "corporate actions" },
  { id: "SCORE", sub: "momentum ranks" },
  { id: "BUILD", sub: "7 portfolios" },
  { id: "PUBLISH", sub: "db + dashboard" },
];

export function PipelineDiagram({ className = "" }: { className?: string }) {
  const W = 960;
  const H = 190;
  const n = PIPELINE_STEPS.length;
  const bw = 128;
  const gap = (W - 48 - n * bw) / (n - 1);
  const y = 58;
  const bh = 62;
  return (
    <div
      className={`mw-dot-canvas relative overflow-hidden rounded-[24px] border border-border/60 bg-card ${className}`}
    >
      <div className="flex items-center justify-between px-6 pt-5">
        <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
          The daily pipeline
        </p>
        <p className="rounded-full border border-border bg-background px-3 py-1 font-mono text-[11px] text-acc1-fg">
          16:30 IST · every trading day
        </p>
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="block w-full"
        role="img"
        aria-label="The daily pipeline: login, fetch NSE 500 and indices, adjust for corporate actions, score momentum, build the seven portfolios, publish to the dashboard, at 16:30 IST every trading day."
      >
        {/* connector rail + travelling light */}
        <line
          x1={24 + bw}
          y1={y + bh / 2}
          x2={W - 24 - bw}
          y2={y + bh / 2}
          className="stroke-border"
          strokeWidth="1.5"
          strokeDasharray="3 5"
        />
        <line
          x1={24}
          y1={y + bh / 2}
          x2={W - 24}
          y2={y + bh / 2}
          className="mw-pipe-light"
          strokeWidth="2"
          pathLength={100}
        />
        {PIPELINE_STEPS.map((s, i) => {
          const x = 24 + i * (bw + gap);
          return (
            <g key={s.id}>
              <rect
                x={x}
                y={y}
                width={bw}
                height={bh}
                rx="10"
                className="fill-[var(--card)] stroke-[var(--border)]"
                strokeWidth="1.5"
              />
              <circle
                cx={x + 14}
                cy={y + 18}
                r="3"
                className={i === n - 1 ? "fill-[var(--primary)]" : "fill-[var(--acc1-line)]"}
              />
              <text
                x={x + 26}
                y={y + 22.5}
                className="fill-[var(--foreground)] font-mono"
                fontSize="12.5"
                fontWeight="500"
              >
                {s.id}
              </text>
              <text
                x={x + 14}
                y={y + 45}
                className="fill-[var(--muted-foreground)]"
                fontSize="11"
              >
                {s.sub}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/* ————— ExhibitFrame — corner-tick media framing ————— */

function Tick({ className }: { className: string }) {
  return (
    <span
      aria-hidden
      className={`pointer-events-none absolute h-3.5 w-3.5 border-foreground/45 ${className}`}
    />
  );
}

export function ExhibitFrame({
  label,
  children,
  caption,
  className = "",
}: {
  label?: string;
  children: ReactNode;
  caption?: ReactNode;
  className?: string;
}) {
  return (
    <figure className={className}>
      <div className="relative p-4">
        <Tick className="left-0 top-0 border-l-2 border-t-2" />
        <Tick className="right-0 top-0 border-r-2 border-t-2" />
        <Tick className="bottom-0 left-0 border-b-2 border-l-2" />
        <Tick className="bottom-0 right-0 border-b-2 border-r-2" />
        {label ? (
          <p className="absolute -top-2.5 left-8 bg-surface-base px-2 font-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
            {label}
          </p>
        ) : null}
        {children}
      </div>
      {caption ? (
        <figcaption className="mt-2 px-4 font-mono text-[11px] leading-[1.6] text-muted-foreground">
          {caption}
        </figcaption>
      ) : null}
    </figure>
  );
}
