"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useTheme } from "next-themes";
import {
  createChart,
  AreaSeries,
  ColorType,
  LineStyle,
  type IChartApi,
  type UTCTimestamp,
} from "lightweight-charts";
import { cn } from "@/lib/utils";

/**
 * Indicator history chart (mission-control detail views): one series with
 * optional horizontal reference bands (median / historical extremes) rendered
 * as price lines, and a client-side range picker slicing an already-fetched
 * full-history payload — no refetch per range. Colors come from the
 * design-system tokens via the same probe pattern as the stock PriceChart.
 */

export interface ReferenceBand {
  value: number;
  label: string;
  tone: "muted" | "warning" | "negative" | "positive";
}

const RANGES: { label: string; days: number | null }[] = [
  { label: "6M", days: 126 },
  { label: "1Y", days: 252 },
  { label: "3Y", days: 756 },
  { label: "5Y", days: 1260 },
  { label: "Max", days: null },
];

function resolveColor(el: HTMLElement, cssVar: string, fallback: string): string {
  const probe = document.createElement("span");
  probe.style.color = `var(${cssVar})`;
  probe.style.display = "none";
  el.appendChild(probe);
  const rgb = getComputedStyle(probe).color;
  el.removeChild(probe);
  return rgb || fallback;
}

export function TimeseriesChart({
  dates,
  values,
  bands = [],
  percent = false,
  defaultRange = "3Y",
  height = 320,
}: {
  dates: string[];
  values: (number | null)[];
  bands?: ReferenceBand[];
  /** Values are 0-1 ratios — display as 0-100%. */
  percent?: boolean;
  defaultRange?: (typeof RANGES)[number]["label"];
  height?: number;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const { theme, resolvedTheme } = useTheme();
  const [range, setRange] = useState(defaultRange);

  const sliced = useMemo(() => {
    const days = RANGES.find((r) => r.label === range)?.days ?? null;
    const start = days === null ? 0 : Math.max(0, dates.length - days);
    const out: { time: UTCTimestamp; value: number }[] = [];
    for (let i = start; i < dates.length; i++) {
      const v = values.at(i);
      if (v === null || v === undefined || Number.isNaN(v)) continue;
      /* eslint-disable-next-line security/detect-object-injection -- parallel arrays, numeric loop index */
      const t = (Date.parse(dates[i]) / 1000) as UTCTimestamp;
      out.push({ time: t, value: percent ? v * 100 : v });
    }
    return out;
  }, [dates, values, range, percent]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el || sliced.length === 0) return;

    const muted = resolveColor(el, "--muted-foreground", "#888");
    const border = resolveColor(el, "--border", "#e5e5e5");
    const chart1 = resolveColor(el, "--chart-1", "#0c7a62");
    const warning = resolveColor(el, "--warning", "#b8860b");
    const negative = resolveColor(el, "--negative", "#a64c42");
    const positive = resolveColor(el, "--positive", "#3f8059");
    const toneColor = { muted, warning, negative, positive } as const;

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
      lastValueVisible: true,
      priceFormat: percent
        ? { type: "custom", formatter: (v: number) => `${v.toFixed(0)}%`, minMove: 0.1 }
        : { type: "price", precision: 1, minMove: 0.1 },
    });
    area.setData(sliced);

    for (const band of bands) {
      area.createPriceLine({
        price: percent ? band.value * 100 : band.value,
        color: toneColor[band.tone],
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: band.label,
      });
    }

    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [sliced, bands, percent, theme, resolvedTheme]);

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
      <div className="flex items-center justify-end gap-1">
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
      <div ref={containerRef} style={{ height }} className="w-full" />
      <div className="flex items-center justify-end text-[10px] text-muted-foreground">
        <a
          href="https://www.tradingview.com"
          target="_blank"
          rel="noopener noreferrer"
          className="underline-offset-2 hover:text-foreground hover:underline"
        >
          Charts by TradingView
        </a>
      </div>
    </div>
  );
}
