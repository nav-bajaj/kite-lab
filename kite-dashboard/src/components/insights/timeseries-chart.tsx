"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useTheme } from "next-themes";
import {
  createChart,
  AreaSeries,
  LineSeries,
  ColorType,
  LineStyle,
  type IChartApi,
  type UTCTimestamp,
} from "lightweight-charts";
import { cn } from "@/lib/utils";

/**
 * Indicator history chart (mission-control detail views): one series with
 * optional horizontal reference bands (median / historical extremes) rendered
 * as price lines, and a client-side range picker. Colors come from the
 * design-system tokens via the same probe pattern as the stock PriceChart.
 *
 * Three opt-in behaviours (first shipped on Advances & declines, 2026-08-21,
 * from the E/F winners in tasks/insights_dashboard_v2/experiments):
 *
 * - `anchor` — a dashed reference line at the first visible day's value, so
 *   "where did this window start" is always on screen. It follows the window
 *   as you pan or zoom. (A green-above/red-below fill was tried first and
 *   dropped — the recolouring on every pan read as noise; founder,
 *   2026-08-22.)
 * - `overlayAxis="left"` — the index overlay gets a VISIBLE left % axis
 *   instead of the hidden scale, so its level is readable anywhere.
 * - `interactive` — drag to pan, wheel/pinch to zoom, axis drag/double-click
 *   to stretch/reset. The full fetched history stays scrollable; the range
 *   pills set the initial window instead of slicing the data. Page scroll is
 *   preserved (wheel zooms, it never scrolls the chart sideways) and both
 *   edges are fixed so you cannot pan into empty space.
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

/** The scope index drawn alongside an indicator, rebased to percent change
 *  from the first day in view — the raw index level carries no information
 *  here, the shape does. With `overlayAxis="left"` the rebased series gets a
 *  real axis; on the legacy hidden scale only the crosshair shows it. */
export interface IndexOverlay {
  label: string;
  dates: string[];
  closes: (number | null)[];
}

export function TimeseriesChart({
  dates,
  values,
  bands = [],
  percent = false,
  defaultRange = "1Y",
  height,
  overlay,
  overlayValueLabel = "Value",
  anchor = false,
  overlayAxis = "hidden",
  interactive = false,
}: {
  dates: string[];
  values: (number | null)[];
  bands?: ReferenceBand[];
  /** Values are 0-1 ratios — display as 0-100%. */
  percent?: boolean;
  defaultRange?: (typeof RANGES)[number]["label"];
  /** Explicit override; omit to use the responsive default. */
  height?: number;
  overlay?: IndexOverlay;
  /** Name for this chart's own series in the crosshair readout. */
  overlayValueLabel?: string;
  /** Dashed reference line at the first visible day's value. */
  anchor?: boolean;
  /** Where the overlay's % scale lives. */
  overlayAxis?: "hidden" | "left";
  /** Enable pan/zoom; range pills then set the initial window only. */
  interactive?: boolean;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const { theme, resolvedTheme } = useTheme();
  const [range, setRange] = useState(defaultRange);
  const [showOverlay, setShowOverlay] = useState(false);
  const [hover, setHover] = useState<{
    day: string;
    value: number;
    overlay: number | null;
  } | null>(null);
  // Held in a ref so the crosshair subscription never has to be a chart
  // rebuild dependency. Assigned in an effect, not during render.
  const onHoverRef = useRef(setHover);
  useEffect(() => {
    onHoverRef.current = setHover;
  }, []);

  const rangeDays = RANGES.find((r) => r.label === range)?.days ?? null;

  // Interactive charts keep the full history in the series (the range pills
  // only choose the initial window, so panning left reveals more); static
  // charts slice as before.
  const sliced = useMemo(() => {
    const days = interactive ? null : rangeDays;
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
  }, [dates, values, rangeDays, percent, interactive]);

  // Raw overlay closes aligned to the chart's span. Rebasing happens at
  // render (and re-render on pan), so the base can follow the window.
  const overlayPoints = useMemo(() => {
    if (!overlay || sliced.length === 0) return [];
    const firstDay = sliced[0].time;
    const out: { time: UTCTimestamp; close: number }[] = [];
    for (let i = 0; i < overlay.dates.length; i++) {
      /* eslint-disable-next-line security/detect-object-injection -- parallel arrays, numeric loop index */
      const t = (Date.parse(overlay.dates[i]) / 1000) as UTCTimestamp;
      if (t < firstDay) continue;
      const v = overlay.closes.at(i);
      if (v === null || v === undefined || Number.isNaN(v) || v <= 0) continue;
      out.push({ time: t, close: v });
    }
    return out;
  }, [overlay, sliced]);

  // Base for the overlay's % rebase — a ref so the crosshair readout stays
  // correct after a pan re-anchors it without resubscribing.
  const overlayBaseRef = useRef<number | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el || sliced.length === 0) return;

    const muted = resolveColor(el, "--muted-foreground", "#888");
    const border = resolveColor(el, "--border", "#e5e5e5");
    const chart1 = resolveColor(el, "--chart-1", "#0c7a62");
    const chart2 = resolveColor(el, "--chart-series-2", "#ad741c");
    const warning = resolveColor(el, "--warning", "#b8860b");
    const negative = resolveColor(el, "--negative", "#a64c42");
    const positive = resolveColor(el, "--positive", "#3f8059");
    const toneColor = { muted, warning, negative, positive } as const;

    const leftAxisVisible = overlayAxis === "left" && showOverlay && overlayPoints.length > 0;

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
      leftPriceScale: leftAxisVisible
        ? { visible: true, borderColor: border, scaleMargins: { top: 0.1, bottom: 0.1 } }
        : { visible: false },
      timeScale: {
        borderColor: border,
        timeVisible: false,
        ...(interactive
          ? { fixLeftEdge: true, fixRightEdge: true, minBarSpacing: 0.05 }
          : {}),
      },
      crosshair: { horzLine: { color: muted }, vertLine: { color: muted } },
      ...(interactive
        ? {
            handleScale: {
              mouseWheel: true,
              pinch: true,
              axisPressedMouseMove: true,
              axisDoubleClickReset: true,
            },
            handleScroll: {
              mouseWheel: false,
              pressedMouseMove: true,
              horzTouchDrag: true,
              vertTouchDrag: false,
            },
            kineticScroll: { touch: true, mouse: true },
          }
        : { handleScale: false, handleScroll: false }),
    });

    // Precision from the series' own magnitude. A fixed 1dp printed the
    // A-D line in stocks as "-15000.0" and collapsed the McClellan
    // oscillator's whole +/-0.14 range onto "0.1" / "0.0" / "-0.1".
    const magnitude = Math.max(...sliced.map((p) => Math.abs(p.value)), 0);
    const precision = magnitude >= 1000 ? 0 : magnitude >= 10 ? 1 : magnitude >= 1 ? 2 : 3;
    const priceFormat = percent
      ? {
          type: "custom" as const,
          formatter: (v: number) => `${v.toFixed(0)}%`,
          minMove: 0.1,
        }
      : { type: "price" as const, precision, minMove: 10 ** -precision };

    // Initial window: interactive charts show the last `rangeDays` bars of
    // the full history; static charts already sliced the data.
    const initialFrom =
      interactive && rangeDays !== null ? Math.max(0, sliced.length - rangeDays) : 0;

    const mainSeries = chart.addSeries(AreaSeries, {
      lineColor: chart1,
      topColor: chart1,
      bottomColor: "transparent",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
      priceFormat,
    });
    mainSeries.setData(sliced);

    const anchorLine = anchor
      ? mainSeries.createPriceLine({
          price: sliced.at(initialFrom)?.value ?? 0,
          color: muted,
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: "start",
        })
      : null;

    for (const band of bands) {
      mainSeries.createPriceLine({
        price: percent ? band.value * 100 : band.value,
        color: toneColor[band.tone],
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: band.label,
      });
    }

    // Overlay: raw closes rebased to % change from the first day in view.
    // rebase() re-runs on pan/zoom so the base is always the left edge.
    let overlaySeries: ReturnType<typeof chart.addSeries> | null = null;
    if (showOverlay && overlayPoints.length > 0) {
      overlaySeries = chart.addSeries(LineSeries, {
        color: overlayAxis === "left" ? chart2 : muted,
        lineWidth: overlayAxis === "left" ? 2 : 1,
        lineStyle: LineStyle.Solid,
        priceScaleId: overlayAxis === "left" ? "left" : "overlay",
        priceLineVisible: false,
        lastValueVisible: overlayAxis === "left",
        priceFormat: {
          type: "custom",
          formatter: (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(0)}%`,
          minMove: 0.1,
        },
      });
      overlaySeries.createPriceLine({
        price: 0,
        color: overlayAxis === "left" ? muted : border,
        lineWidth: 1,
        lineStyle: LineStyle.Dotted,
        axisLabelVisible: false,
        title: "",
      });
      if (overlayAxis !== "left") {
        chart.priceScale("overlay").applyOptions({
          scaleMargins: { top: 0.1, bottom: 0.1 },
          visible: false,
        });
      }
    }

    const rebaseOverlay = (fromIdx: number) => {
      if (!overlaySeries) return;
      const fromTime = sliced.at(Math.min(fromIdx, sliced.length - 1))?.time ?? 0;
      const first = overlayPoints.find((p) => p.time >= fromTime) ?? overlayPoints.at(0);
      if (!first) return;
      overlayBaseRef.current = first.close;
      overlaySeries.setData(
        overlayPoints.map((p) => ({ time: p.time, value: (p.close / first.close - 1) * 100 })),
      );
    };
    rebaseOverlay(initialFrom);

    // Crosshair readout: the day, the indicator's own value and the
    // overlay's percent change, shown above the chart rather than in a
    // floating tooltip. Both series are named so neither number is
    // ambiguous, and the colours are token-derived so it reads in every
    // palette (founder, 2026-08-15).
    const indicatorAt = new Map(sliced.map((p) => [p.time as number, p.value]));
    const overlayCloseAt = new Map(overlayPoints.map((p) => [p.time as number, p.close]));
    chart.subscribeCrosshairMove((param) => {
      const time = param.time as number | undefined;
      const v = time === undefined ? undefined : indicatorAt.get(time);
      if (time === undefined || v === undefined) {
        onHoverRef.current(null);
        return;
      }
      const close = overlayCloseAt.get(time);
      const base = overlayBaseRef.current;
      onHoverRef.current({
        day: new Date(time * 1000).toISOString().slice(0, 10),
        value: v,
        overlay:
          showOverlay && close !== undefined && base !== null && base > 0
            ? (close / base - 1) * 100
            : null,
      });
    });

    // Pan/zoom re-anchoring: the start line and the overlay's rebase both
    // follow the first visible day.
    let lastFrom = initialFrom;
    let raf = 0;
    if (interactive && (anchorLine || overlaySeries)) {
      chart.timeScale().subscribeVisibleLogicalRangeChange((lr) => {
        if (!lr) return;
        cancelAnimationFrame(raf);
        raf = requestAnimationFrame(() => {
          const from = Math.max(0, Math.min(sliced.length - 1, Math.round(lr.from)));
          if (from === lastFrom) return;
          lastFrom = from;
          if (anchorLine) {
            anchorLine.applyOptions({ price: sliced.at(from)?.value ?? 0 });
          }
          rebaseOverlay(from);
        });
      });
    }

    if (interactive && rangeDays !== null) {
      chart.timeScale().setVisibleLogicalRange({ from: initialFrom, to: sliced.length });
    } else {
      chart.timeScale().fitContent();
    }
    return () => {
      cancelAnimationFrame(raf);
      chart.remove();
    };
  }, [
    sliced,
    overlayPoints,
    showOverlay,
    bands,
    percent,
    theme,
    resolvedTheme,
    anchor,
    overlayAxis,
    interactive,
    rangeDays,
  ]);

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
      <div className="flex flex-wrap items-center justify-end gap-1">
        {overlay && (
          <button
            onClick={() => setShowOverlay((v) => !v)}
            aria-pressed={showOverlay}
            title={`Overlay ${overlay.label}, rebased to 0% at the first day in view`}
            className={cn(
              "mr-auto flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-[12px] font-medium transition-colors",
              showOverlay
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border text-foreground hover:bg-muted",
            )}
          >
            <span
              aria-hidden
              className="inline-block h-0.5 w-3.5 rounded-full"
              style={{
                backgroundColor: showOverlay ? "currentColor" : "var(--muted-foreground)",
              }}
            />
            {overlay.label}
          </button>
        )}
        {RANGES.map((r) => (
          <button
            key={r.label}
            onClick={() => setRange(r.label)}
            aria-pressed={range === r.label}
            className={cn(
              "rounded-md px-3 py-1.5 font-mono text-[11px] transition-colors lg:px-2.5 lg:py-1",
              range === r.label
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            {r.label}
          </button>
        ))}
      </div>
      <div className="flex min-h-[18px] flex-wrap items-baseline gap-x-3 font-mono text-[11px] tabular-nums">
        {hover ? (
          <>
            <span className="text-foreground">
              {new Date(hover.day).toLocaleDateString("en-IN", {
                day: "2-digit",
                month: "short",
                year: "numeric",
              })}
            </span>
            <span className="text-[color:var(--chart-1)]">
              {overlayValueLabel} {percent ? `${hover.value.toFixed(1)}%` : hover.value.toFixed(2)}
            </span>
            {hover.overlay !== null && overlay && (
              <span
                className={
                  overlayAxis === "left"
                    ? "text-[color:var(--chart-series-2)]"
                    : "text-muted-foreground"
                }
              >
                {overlay.label} {hover.overlay >= 0 ? "+" : ""}
                {hover.overlay.toFixed(1)}%
              </span>
            )}
          </>
        ) : (
          <span className="text-muted-foreground/70">
            hover the chart for that day&apos;s values
          </span>
        )}
      </div>
      <div
        ref={containerRef}
        style={height ? { height } : undefined}
        className={cn(!height && "h-[260px] sm:h-[320px] lg:h-[400px]", "w-full")}
      />
      {overlay && showOverlay && (
        <p className="text-[11px] text-muted-foreground">
          {overlayAxis === "left"
            ? `${overlay.label} is drawn as percent change from the first day in view, on the left axis — 0% means unchanged since the left edge.`
            : `${overlay.label} is drawn as percent change from the left edge of the visible window, on its own scale — read the shape against the indicator, not the level.`}
        </p>
      )}
      {anchor && (
        <p className="text-[11px] text-muted-foreground">
          The dashed line marks where the series started this window — above
          it means net gain since the left edge, below it net loss.
        </p>
      )}
      <div className="flex items-center justify-between gap-3 text-[10px] text-muted-foreground">
        <span>
          {interactive
            ? "drag to pan · scroll or pinch to zoom · double-click an axis to reset it"
            : ""}
        </span>
        <a
          href="https://www.tradingview.com"
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 underline-offset-2 hover:text-foreground hover:underline"
        >
          Charts by TradingView
        </a>
      </div>
    </div>
  );
}
