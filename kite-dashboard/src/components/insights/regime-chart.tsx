"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useTheme } from "next-themes";
import {
  createChart,
  HistogramSeries,
  LineSeries,
  ColorType,
  LineStyle,
  type IChartApi,
  type UTCTimestamp,
} from "lightweight-charts";
import { cn } from "@/lib/utils";
import { regimeLabel } from "@/lib/insights-api";

/**
 * Regime chart: the scope's index drawn as a line over a light background
 * tint that carries the regime of each day. Reading the regime against the
 * price it produced is the point — a bare episode timeline hid what the
 * market actually did (founder, 2026-08-15).
 *
 * The tint is a full-height histogram on a hidden overlay price scale, one
 * bar per trading day; the index line sits on the visible scale above it.
 */

const RANGES: { label: string; days: number | null }[] = [
  { label: "6M", days: 126 },
  { label: "1Y", days: 252 },
  { label: "3Y", days: 756 },
  { label: "5Y", days: 1260 },
  { label: "Max", days: null },
];

// Kept module-local: a plain constant exported from a "use client" file
// arrives in a server component as a client-reference proxy, not a value.
const REGIME_ORDER = ["TREND_BULL", "DRIFT", "STRETCHED", "STRESS"] as const;

const REGIME_VAR: Record<string, string> = {
  TREND_BULL: "--positive",
  DRIFT: "--muted-foreground",
  STRETCHED: "--warning",
  STRESS: "--negative",
};

function resolveColor(el: HTMLElement, cssVar: string, fallback: string): string {
  const probe = document.createElement("span");
  probe.style.color = `var(${cssVar})`;
  probe.style.display = "none";
  el.appendChild(probe);
  const rgb = getComputedStyle(probe).color;
  el.removeChild(probe);
  return rgb || fallback;
}

/** "rgb(r, g, b)" | "rgba(r, g, b, a)" → "rgba(r, g, b, alpha)". */
function withAlpha(color: string, alpha: number): string {
  const nums = color.match(/[\d.]+/g);
  if (!nums || nums.length < 3) return color;
  return `rgba(${nums[0]}, ${nums[1]}, ${nums[2]}, ${alpha})`;
}

interface SlicedSeries {
  line: { time: UTCTimestamp; value: number }[];
  tint: { time: UTCTimestamp; regime: string }[];
}

function buildChart(el: HTMLDivElement, sliced: SlicedSeries): IChartApi {
  const muted = resolveColor(el, "--muted-foreground", "#888");
  const border = resolveColor(el, "--border", "#e5e5e5");
  const foreground = resolveColor(el, "--foreground", "#1a1a1a");
  const tintFor = Object.fromEntries(
    REGIME_ORDER.map((r) => [
      r,
      /* eslint-disable-next-line security/detect-object-injection -- r iterates a literal tuple */
      withAlpha(resolveColor(el, REGIME_VAR[r], muted), r === "DRIFT" ? 0.07 : 0.14),
    ]),
  ) as Record<string, string>;

  const chart = createChart(el, {
    autoSize: true,
    layout: {
      background: { type: ColorType.Solid, color: "transparent" },
      textColor: muted,
      fontFamily: "inherit",
      attributionLogo: false,
    },
    grid: {
      vertLines: { visible: false },
      horzLines: { color: border, style: LineStyle.Dotted },
    },
    rightPriceScale: { borderColor: border },
    timeScale: { borderColor: border, timeVisible: false },
    crosshair: { horzLine: { color: muted }, vertLine: { color: muted } },
    handleScale: false,
    handleScroll: false,
  });

  // Background tint first so the index line draws over it.
  const tint = chart.addSeries(HistogramSeries, {
    priceScaleId: "regime-tint",
    base: 0,
    priceLineVisible: false,
    lastValueVisible: false,
    priceFormat: { type: "volume" },
  });
  tint.setData(
    sliced.tint.map((p) => ({
      time: p.time,
      value: 1,
      color: tintFor[p.regime] ?? tintFor.DRIFT,
    })),
  );
  chart.priceScale("regime-tint").applyOptions({
    scaleMargins: { top: 0, bottom: 0 },
    visible: false,
    autoScale: false,
  });

  const line = chart.addSeries(LineSeries, {
    color: foreground,
    lineWidth: 2,
    priceLineVisible: false,
    lastValueVisible: true,
    priceFormat: { type: "price", precision: 0, minMove: 1 },
  });
  line.setData(sliced.line);
  chart.priceScale("right").applyOptions({ scaleMargins: { top: 0.08, bottom: 0.08 } });
  chart.timeScale().fitContent();
  return chart;
}

export function RegimeChart({
  dates,
  closes,
  regimes,
  indexLabel,
  defaultRange = "1Y",
  height = 340,
}: {
  dates: string[];
  closes: (number | null)[];
  regimes: string[];
  indexLabel: string;
  defaultRange?: (typeof RANGES)[number]["label"];
  height?: number;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const { theme, resolvedTheme } = useTheme();
  const [range, setRange] = useState(defaultRange);

  const sliced = useMemo(() => {
    const days = RANGES.find((r) => r.label === range)?.days ?? null;
    const start = days === null ? 0 : Math.max(0, dates.length - days);
    const line: { time: UTCTimestamp; value: number }[] = [];
    const tint: { time: UTCTimestamp; regime: string }[] = [];
    for (let i = start; i < dates.length; i++) {
      const v = closes.at(i);
      if (v === null || v === undefined || Number.isNaN(v)) continue;
      /* eslint-disable-next-line security/detect-object-injection -- parallel arrays, numeric loop index */
      const t = (Date.parse(dates[i]) / 1000) as UTCTimestamp;
      line.push({ time: t, value: v });
      tint.push({ time: t, regime: regimes.at(i) ?? "DRIFT" });
    }
    return { line, tint };
  }, [dates, closes, regimes, range]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el || sliced.line.length === 0) return;

    // Build on the next frame. Switching palette swaps the token values on
    // <html>; reading them in the same commit yields the outgoing palette's
    // colors, which is how a white line ends up on a white card.
    let chart: IChartApi | null = null;
    const frame = requestAnimationFrame(() => {
      chart = buildChart(el, sliced);
    });
    return () => {
      cancelAnimationFrame(frame);
      chart?.remove();
    };
  }, [sliced, theme, resolvedTheme]);

  if (dates.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        History is not available right now — it will reappear after the next
        data refresh.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-[12px] text-muted-foreground">{indexLabel}</span>
        <div className="flex items-center gap-1">
          {RANGES.map((r) => (
            <button
              key={r.label}
              onClick={() => setRange(r.label)}
              aria-pressed={range === r.label}
              className={cn(
                "rounded-md px-2.5 py-1 font-mono text-[11px] transition-colors",
                range === r.label
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>
      <div ref={containerRef} style={{ height }} className="w-full" />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-4">
          {REGIME_ORDER.map((r) => (
            <span
              key={r}
              className="flex items-center gap-1.5 text-[12px] text-muted-foreground"
            >
              <span
                className="inline-block h-2.5 w-2.5 rounded-[3px]"
                /* eslint-disable-next-line security/detect-object-injection -- r iterates a literal tuple */
                style={{ backgroundColor: `var(${REGIME_VAR[r]})`, opacity: 0.55 }}
              />
              {regimeLabel(r)}
            </span>
          ))}
        </div>
        <a
          href="https://www.tradingview.com"
          target="_blank"
          rel="noopener noreferrer"
          className="text-[10px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
        >
          Charts by TradingView
        </a>
      </div>
    </div>
  );
}
