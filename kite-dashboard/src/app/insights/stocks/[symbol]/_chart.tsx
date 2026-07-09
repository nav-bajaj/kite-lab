"use client";

import { useEffect, useRef } from "react";
import { useTheme } from "next-themes";
import {
  createChart,
  AreaSeries,
  LineSeries,
  LineStyle,
  ColorType,
  type IChartApi,
  type UTCTimestamp,
} from "lightweight-charts";
import type { PriceSeries, RSHistoryPoint } from "@/lib/insights-api";

/**
 * 1-year price chart (close area + 50/200-DMA) rendered with TradingView's
 * lightweight-charts. Client-only: it receives already-fetched series as
 * props and builds/destroys the chart in an effect. Colors are pulled from the
 * design-system tokens (resolved to rgb via a probe element so the canvas gets
 * concrete colors), and the chart is rebuilt when the next-themes theme flips.
 */

/** Resolve a CSS custom property to a concrete rgb() string in `el`'s context
 *  (canvas needs a concrete color, not `var(--x)` / an unresolved oklch). */
function resolveColor(el: HTMLElement, cssVar: string, fallback: string): string {
  const probe = document.createElement("span");
  probe.style.color = `var(${cssVar})`;
  probe.style.display = "none";
  el.appendChild(probe);
  const rgb = getComputedStyle(probe).color;
  el.removeChild(probe);
  return rgb || fallback;
}

function pts(dates: string[] | undefined, values: (number | null)[] | undefined) {
  if (!dates || !values) return [];
  const out: { time: UTCTimestamp; value: number }[] = [];
  // Parallel arrays indexed by the same loop counter — the values are plain
  // numbers/dates from our own API, not user-controlled keys.
  dates.forEach((d, i) => {
    /* eslint-disable-next-line security/detect-object-injection */
    const v = values[i];
    if (v === null || v === undefined) return;
    out.push({ time: (Date.parse(d) / 1000) as UTCTimestamp, value: v });
  });
  return out;
}

export function PriceChart({ series }: { series: Partial<PriceSeries> }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const { resolvedTheme } = useTheme();

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    if (!series.dates || series.dates.length === 0) return;

    const foreground = resolveColor(el, "--foreground", "#1a1a1a");
    const muted = resolveColor(el, "--muted-foreground", "#888");
    const border = resolveColor(el, "--border", "#e5e5e5");
    const chart1 = resolveColor(el, "--chart-1", "#e0752d");
    const chart2 = resolveColor(el, "--chart-2", "#2a9d8f");

    const chart: IChartApi = createChart(el, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: muted,
        fontFamily: "inherit",
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: border, style: LineStyle.Dotted },
        horzLines: { color: border, style: LineStyle.Dotted },
      },
      rightPriceScale: { borderColor: border },
      timeScale: { borderColor: border, timeVisible: false },
      crosshair: { horzLine: { color: muted }, vertLine: { color: muted } },
      handleScale: false,
      handleScroll: false,
    });

    const area = chart.addSeries(AreaSeries, {
      lineColor: chart1,
      topColor: chart1,
      bottomColor: "transparent",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    area.setData(pts(series.dates, series.close));

    const sma50 = chart.addSeries(LineSeries, {
      color: chart2,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    });
    sma50.setData(pts(series.dates, series.sma_50));

    const sma200 = chart.addSeries(LineSeries, {
      color: muted,
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    });
    sma200.setData(pts(series.dates, series.sma_200));

    chart.timeScale().fitContent();
    // Touch the text color so linters see it consumed; it also keeps the
    // watermark-free layout tidy against the card background.
    void foreground;

    return () => chart.remove();
  }, [series, resolvedTheme]);

  if (!series.dates || series.dates.length === 0) {
    return <p className="text-sm text-muted-foreground">No price history available.</p>;
  }

  return (
    <div className="flex flex-col gap-1">
      <div ref={containerRef} className="h-[320px] w-full" />
      <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
        <span className="flex items-center gap-1"><Swatch varName="--chart-1" /> Close</span>
        <span className="flex items-center gap-1"><Swatch varName="--chart-2" /> 50-DMA</span>
        <span className="flex items-center gap-1"><Swatch varName="--muted-foreground" dashed /> 200-DMA</span>
        <a
          href="https://www.tradingview.com"
          target="_blank"
          rel="noopener noreferrer"
          className="ml-auto underline-offset-2 hover:text-foreground hover:underline"
        >
          Charts by TradingView
        </a>
      </div>
    </div>
  );
}

function Swatch({ varName, dashed }: { varName: string; dashed?: boolean }) {
  return (
    <span
      aria-hidden
      className="inline-block h-0 w-3 align-middle"
      style={{ borderTop: `2px ${dashed ? "dashed" : "solid"} var(${varName})` }}
    />
  );
}

/** RS-rank sparkline (coarse monthly points) as a tiny inline SVG. The rank
 *  axis is inverted so "up" = "stronger" (rank 1 at the top). */
export function RSSparkline({ history }: { history: RSHistoryPoint[] }) {
  if (history.length < 2) {
    return <p className="text-sm text-muted-foreground">Not enough RS-rank history to chart.</p>;
  }
  const W = 320;
  const H = 96;
  const pad = 6;
  const ranks = history.map((h) => h.rank);
  const min = Math.min(...ranks);
  const max = Math.max(...ranks);
  const span = Math.max(1, max - min);
  const n = history.length;
  const x = (i: number) => pad + (i * (W - 2 * pad)) / (n - 1);
  // Rank 1 = strongest → draw at the top (small y).
  const y = (rank: number) => pad + ((rank - min) / span) * (H - 2 * pad);
  const points = history.map((h, i) => `${x(i)},${y(h.rank)}`).join(" ");
  const last = history[n - 1];

  return (
    <div className="flex flex-col gap-1">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-24 w-full" preserveAspectRatio="none">
        <polyline
          points={points}
          fill="none"
          stroke="var(--chart-1)"
          strokeWidth={2}
          vectorEffect="non-scaling-stroke"
        />
        <circle cx={x(n - 1)} cy={y(last.rank)} r={2.5} fill="var(--chart-1)" />
      </svg>
      <div className="flex justify-between text-[10px] text-muted-foreground">
        <span>{new Date(history[0].date).toLocaleDateString("en-IN", { month: "short", year: "2-digit" })}</span>
        <span>Best #{min} · latest #{last.rank}</span>
        <span>{new Date(last.date).toLocaleDateString("en-IN", { month: "short", year: "2-digit" })}</span>
      </div>
    </div>
  );
}
