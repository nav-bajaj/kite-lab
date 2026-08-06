"use client";

import { useEffect, useRef } from "react";

import { cn } from "@/lib/utils";

/**
 * Hero motion v2 (PREFERENCES.md P11, base.org register): an abstract quant
 * texture on 2D canvas — a dithered data-point field breathing under value
 * noise, with clusters of candlesticks that fade in, breathe, and dissolve.
 * No red/green: up-candles are filled primary, down-candles are outlined, so
 * identity and meaning stay separate on a marketing surface.
 *
 * Colors resolve from CSS tokens at runtime and re-resolve when the theme
 * class / palette attribute changes, so the scene follows light/dark live.
 * prefers-reduced-motion renders a single static frame. rAF stops on unmount;
 * browsers pause rAF on hidden tabs.
 */

type Candle = {
  x: number;
  bodyTop: number;
  bodyH: number;
  wickTop: number;
  wickH: number;
  up: boolean;
};

type Cluster = {
  candles: Candle[];
  born: number;
  life: number; // ms of hold phase
  gone?: boolean;
};

const FADE_IN = 1400;
const FADE_OUT = 1800;

function makeCluster(w: number, h: number, now: number, compact: boolean): Cluster {
  const count = compact ? 5 + Math.floor(Math.random() * 3) : 7 + Math.floor(Math.random() * 5);
  const cw = 7;
  const gap = 5;
  const clusterW = count * (cw + gap);
  const x0 = 20 + Math.random() * Math.max(40, w - clusterW - 40);
  const mid = h * (0.35 + Math.random() * 0.3);
  const amp = h * (compact ? 0.16 : 0.2);
  let level = mid;
  const candles: Candle[] = [];
  for (let i = 0; i < count; i++) {
    const drift = (Math.random() - 0.48) * amp * 0.6;
    const open = level;
    const close = Math.max(14, Math.min(h - 14, level + drift));
    level = close;
    const top = Math.min(open, close);
    const bodyH = Math.max(3, Math.abs(close - open));
    const wickPad = (0.3 + Math.random() * 0.7) * amp * 0.35;
    candles.push({
      x: x0 + i * (cw + gap),
      bodyTop: top,
      bodyH,
      wickTop: top - wickPad,
      wickH: bodyH + wickPad * 2,
      up: close <= open,
    });
  }
  return { candles, born: now, life: 3800 + Math.random() * 3200 };
}

// Deterministic 2D value noise, smoothed; cheap enough to run per-dot.
function hash(ix: number, iy: number): number {
  const s = Math.sin(ix * 127.1 + iy * 311.7) * 43758.5453;
  return s - Math.floor(s);
}
function noise(x: number, y: number): number {
  const ix = Math.floor(x);
  const iy = Math.floor(y);
  const fx = x - ix;
  const fy = y - iy;
  const sx = fx * fx * (3 - 2 * fx);
  const sy = fy * fy * (3 - 2 * fy);
  const a = hash(ix, iy);
  const b = hash(ix + 1, iy);
  const c = hash(ix, iy + 1);
  const d = hash(ix + 1, iy + 1);
  return a + (b - a) * sx + (c - a) * sy + (a - b - c + d) * sx * sy;
}

function readTokens(el: HTMLElement) {
  const cs = getComputedStyle(el);
  return {
    primary: cs.getPropertyValue("--primary").trim() || "#0A5CFF",
    secondary: cs.getPropertyValue("--secondary").trim() || "#E8A33D",
  };
}

export function HeroQuant({ className }: { className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let raf = 0;
    let tokens = readTokens(canvas);
    let clusters: Cluster[] = [];
    let w = 0;
    let h = 0;
    let dpr = 1;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = rect.width;
      h = rect.height;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const compact = () => w < 720;

    const drawDither = (t: number) => {
      const spacing = compact() ? 14 : 11;
      const nt = t * 0.00016;
      for (let gx = 0; gx < w; gx += spacing) {
        for (let gy = 0; gy < h; gy += spacing) {
          // vertical falloff keeps the field a horizontal stream, denser mid-band
          const band = 1 - Math.abs(gy / h - 0.5) * 1.7;
          if (band <= 0.05) continue;
          const n = noise(gx * 0.02, gy * 0.035 + nt * 3) * 0.6 + noise(gx * 0.005 - nt, gy * 0.01) * 0.4;
          const v = n * band;
          if (v < 0.32) continue;
          const spark = n > 0.86;
          const alpha = Math.min(0.55, (v - 0.32) * 1.15);
          ctx.fillStyle = spark ? tokens.secondary : tokens.primary;
          ctx.globalAlpha = spark ? Math.min(0.8, alpha + 0.2) : alpha;
          const size = spark ? 2.6 : 2;
          ctx.fillRect(gx, gy, size, size);
        }
      }
      ctx.globalAlpha = 1;
    };

    const drawCluster = (c: Cluster, now: number) => {
      const age = now - c.born;
      let a: number;
      if (age < FADE_IN) a = age / FADE_IN;
      else if (age < FADE_IN + c.life) a = 1;
      else if (age < FADE_IN + c.life + FADE_OUT) a = 1 - (age - FADE_IN - c.life) / FADE_OUT;
      else {
        c.gone = true;
        return;
      }
      // breathe: slow vertical scale around each candle's own center
      const breath = reduce ? 1 : 1 + Math.sin(now * 0.0009 + c.born) * 0.035;
      ctx.lineWidth = 1;
      for (const cd of c.candles) {
        const cy = cd.bodyTop + cd.bodyH / 2;
        const bodyH = cd.bodyH * breath;
        const wickH = cd.wickH * breath;
        const bodyTop = cy - bodyH / 2;
        const wickTop = cy - (cy - cd.wickTop) * breath;
        ctx.globalAlpha = a * 0.5;
        ctx.strokeStyle = tokens.primary;
        ctx.beginPath();
        ctx.moveTo(cd.x + 3.5, wickTop);
        ctx.lineTo(cd.x + 3.5, wickTop + wickH);
        ctx.stroke();
        if (cd.up) {
          ctx.globalAlpha = a * 0.85;
          ctx.fillStyle = tokens.primary;
          ctx.fillRect(cd.x, bodyTop, 7, bodyH);
        } else {
          ctx.globalAlpha = a * 0.6;
          ctx.strokeStyle = tokens.primary;
          ctx.strokeRect(cd.x + 0.5, bodyTop + 0.5, 6, Math.max(2, bodyH - 1));
        }
      }
      ctx.globalAlpha = 1;
    };

    const frame = (now: number) => {
      ctx.clearRect(0, 0, w, h);
      drawDither(now);
      const target = compact() ? 2 : 4;
      clusters = clusters.filter((c) => !c.gone);
      while (clusters.length < target) {
        // stagger newborn clusters so they don't sync up
        clusters.push(makeCluster(w, h, now - Math.random() * FADE_IN, compact()));
      }
      for (const c of clusters) drawCluster(c, now);
    };

    const loop = (now: number) => {
      frame(now);
      raf = requestAnimationFrame(loop);
    };

    resize();
    if (reduce) {
      // static: one deterministic frame, clusters at full opacity
      clusters = [makeCluster(w, h, -FADE_IN, compact()), makeCluster(w, h, -FADE_IN, compact())];
      frame(FADE_IN + 1);
    } else {
      raf = requestAnimationFrame(loop);
    }

    const onResize = () => {
      resize();
      clusters = [];
      if (reduce) frame(FADE_IN + 1);
    };
    window.addEventListener("resize", onResize);

    // follow live theme/palette switches
    const mo = new MutationObserver(() => {
      tokens = readTokens(canvas);
      if (reduce) frame(FADE_IN + 1);
    });
    mo.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class", "data-palette"],
    });

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      mo.disconnect();
    };
  }, []);

  return <canvas ref={ref} aria-hidden className={cn("h-full w-full", className)} />;
}
