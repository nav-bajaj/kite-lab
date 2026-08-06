"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Dev-only tuning panel for the hero grain (design_studies loop 13). Drives
 * the CSS vars consumed by .mw-hero-grain/.mw-hero-drama pseudo-layers:
 *   --grain-url (regenerated SVG noise), --grain-opacity, --grain-blend,
 *   --grain-fine-opacity.
 * "copy values" puts the current settings on the clipboard so the winning
 * numbers can be baked into globals.css. Never ships to production — remove
 * the render in page.tsx when the study closes.
 */

type Settings = {
  coarseness: number; // baseFrequency, lower = chunkier
  punch: number; // contrast table steepness 0..0.45
  opacity: number;
  blend: string;
  fineOpacity: number;
};

const DEFAULTS: Settings = {
  coarseness: 0.34,
  punch: 0.1,
  opacity: 0.5,
  blend: "overlay",
  fineOpacity: 0.1,
};

function grainUrl(coarseness: number, punch: number): string {
  const table = `0 ${punch.toFixed(2)} ${(1 - punch).toFixed(2)} 1`;
  const svg =
    `<svg xmlns='http://www.w3.org/2000/svg' width='420' height='420'>` +
    `<filter id='n'>` +
    `<feTurbulence type='fractalNoise' baseFrequency='${coarseness.toFixed(2)}' numOctaves='3' stitchTiles='stitch'/>` +
    `<feColorMatrix type='saturate' values='0'/>` +
    `<feComponentTransfer>` +
    `<feFuncR type='table' tableValues='${table}'/>` +
    `<feFuncG type='table' tableValues='${table}'/>` +
    `<feFuncB type='table' tableValues='${table}'/>` +
    `</feComponentTransfer>` +
    `</filter>` +
    `<rect width='100%' height='100%' filter='url(%23n)'/>` +
    `</svg>`;
  return `url("data:image/svg+xml,${encodeURIComponent(svg).replaceAll("%2523", "%23")}")`;
}

export function GrainTuner() {
  const [s, setS] = useState<Settings>(DEFAULTS);
  const [open, setOpen] = useState(true);
  const [copied, setCopied] = useState(false);
  const heroRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    heroRef.current = document.querySelector(
      ".mw-hero-drama, .mw-hero-grain",
    ) as HTMLElement | null;
  }, []);

  const apply = useCallback((next: Settings) => {
    setS(next);
    const el = heroRef.current;
    if (!el) return;
    el.style.setProperty("--grain-url", grainUrl(next.coarseness, next.punch));
    el.style.setProperty("--grain-opacity", String(next.opacity));
    el.style.setProperty("--grain-blend", next.blend);
    el.style.setProperty("--grain-fine-opacity", String(next.fineOpacity));
  }, []);

  const copy = () => {
    const summary =
      `grain settings: baseFrequency=${s.coarseness.toFixed(2)}, ` +
      `table=[0 ${s.punch.toFixed(2)} ${(1 - s.punch).toFixed(2)} 1], ` +
      `opacity=${s.opacity.toFixed(2)}, blend=${s.blend}, ` +
      `fineOpacity=${s.fineOpacity.toFixed(2)}`;
    void navigator.clipboard.writeText(summary).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  const row = "flex items-center justify-between gap-3";
  const label = "font-mono text-[11px] text-muted-foreground";

  return (
    <div className="fixed bottom-4 right-4 z-50 w-[260px] rounded-lg border border-border bg-card/95 p-4 shadow-lg backdrop-blur">
      <div className={row}>
        <span className="font-mono text-xs font-semibold text-foreground">
          grain tuner (dev)
        </span>
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="font-mono text-xs text-muted-foreground hover:text-foreground"
        >
          {open ? "hide" : "show"}
        </button>
      </div>
      {open && (
        <div className="mt-3 flex flex-col gap-3">
          <label className={row}>
            <span className={label}>coarseness {s.coarseness.toFixed(2)}</span>
            <input
              type="range"
              min="0.12"
              max="0.9"
              step="0.02"
              value={s.coarseness}
              onChange={(e) =>
                apply({ ...s, coarseness: Number(e.target.value) })
              }
              className="w-32 accent-[var(--primary)]"
            />
          </label>
          <label className={row}>
            <span className={label}>punch {s.punch.toFixed(2)}</span>
            <input
              type="range"
              min="0"
              max="0.45"
              step="0.05"
              value={s.punch}
              onChange={(e) => apply({ ...s, punch: Number(e.target.value) })}
              className="w-32 accent-[var(--primary)]"
            />
          </label>
          <label className={row}>
            <span className={label}>opacity {s.opacity.toFixed(2)}</span>
            <input
              type="range"
              min="0"
              max="0.9"
              step="0.05"
              value={s.opacity}
              onChange={(e) => apply({ ...s, opacity: Number(e.target.value) })}
              className="w-32 accent-[var(--primary)]"
            />
          </label>
          <label className={row}>
            <span className={label}>fine layer {s.fineOpacity.toFixed(2)}</span>
            <input
              type="range"
              min="0"
              max="0.4"
              step="0.02"
              value={s.fineOpacity}
              onChange={(e) =>
                apply({ ...s, fineOpacity: Number(e.target.value) })
              }
              className="w-32 accent-[var(--primary)]"
            />
          </label>
          <label className={row}>
            <span className={label}>blend</span>
            <select
              value={s.blend}
              onChange={(e) => apply({ ...s, blend: e.target.value })}
              className="rounded border border-border bg-background px-1.5 py-1 font-mono text-[11px] text-foreground"
            >
              <option value="overlay">overlay</option>
              <option value="soft-light">soft-light</option>
              <option value="normal">normal</option>
              <option value="multiply">multiply</option>
              <option value="screen">screen</option>
            </select>
          </label>
          <div className="flex items-center justify-between pt-1">
            <button
              type="button"
              onClick={() => apply(DEFAULTS)}
              className="font-mono text-[11px] text-muted-foreground hover:text-foreground"
            >
              reset
            </button>
            <button
              type="button"
              onClick={copy}
              className="rounded border border-border px-2 py-1 font-mono text-[11px] text-foreground hover:border-primary"
            >
              {copied ? "copied" : "copy values"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
