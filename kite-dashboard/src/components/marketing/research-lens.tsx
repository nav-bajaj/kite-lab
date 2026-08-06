"use client";

import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

/**
 * Research lens (design_studies_clay, loop 21 — founder request for the
 * section-03 card): a magnifying glass drifts over a faint dither field of
 * small cubes; inside the glass the field is magnified and individual cells
 * light up like data points being found — research as "looking closely".
 *
 * Same idiom as HeroFlow: token-exact colors resolved from CSS vars at
 * mount and re-resolved on palette/theme change; DPR-aware; static frame
 * under reduced-motion; pauses on hidden tab; purely decorative.
 */

let INK = "27,26,23"; // --foreground fallback
let PRIME = "10,92,255"; // --primary fallback
let SUN = "245,183,30"; // --secondary fallback

function cssColorToChannels(v: string): string | null {
  const value = v.trim();
  const hex = /^#([0-9a-f]{6})$/i.exec(value);
  if (hex) {
    const n = parseInt(hex[1], 16);
    return `${(n >> 16) & 255},${(n >> 8) & 255},${n & 255}`;
  }
  const rgb = /^rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)/.exec(value);
  if (rgb) return `${rgb[1]},${rgb[2]},${rgb[3]}`;
  return null;
}

function resolveColors(el: HTMLElement) {
  const cs = getComputedStyle(el);
  INK = cssColorToChannels(cs.getPropertyValue("--foreground")) ?? INK;
  PRIME = cssColorToChannels(cs.getPropertyValue("--primary")) ?? PRIME;
  SUN = cssColorToChannels(cs.getPropertyValue("--secondary")) ?? SUN;
}

// ---- dither field ----
const PITCH = 16; // grid pitch (px)
const CUBE = 3; // base cube size (px)
const BASE_ALPHA = 0.05; // faintest cell
const BASE_RANGE = 0.09; // added per the Bayer threshold
// 4x4 Bayer matrix — ordered-dither thresholds give the field its texture
const BAYER = [
  [0, 8, 2, 10],
  [12, 4, 14, 6],
  [3, 11, 1, 9],
  [15, 7, 13, 5],
];

// ---- lens ----
const LENS_R_FRAC = 0.3; // of min(W, H)
const MAG = 1.75; // magnification inside the glass
const DRIFT_X = 0.14; // lissajous amplitudes (fraction of W/H)
const DRIFT_Y = 0.16;
const DRIFT_SEC_X = 19;
const DRIFT_SEC_Y = 13;
const RING_ALPHA = 0.82;
const FILL_ALPHA = 0.05; // primary tint of the glass itself

// ---- data-point sparks (inside the lens) ----
const SPARK_EVERY = 0.55; // spawn cadence (s)
const SPARK_MAX = 7;
const SPARK_IN = 0.35; // fade in (s)
const SPARK_HOLD = 0.7;
const SPARK_OUT = 0.9;
const SPARK_GLOW_R = 13;

type Spark = { col: number; row: number; age: number; hue: "prime" | "sun" };

export function ResearchLens({ className }: { className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const [paletteEpoch, setPaletteEpoch] = useState(0);

  useEffect(() => {
    const observer = new MutationObserver(() => setPaletteEpoch((e) => e + 1));
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class", "data-palette"],
    });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    resolveColors(canvas);

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let W = 0;
    let H = 0;
    let time = 0;
    let sparks: Spark[] = [];
    let spawnClock = 0;

    const build = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = canvas.clientWidth;
      H = canvas.clientHeight;
      if (W === 0 || H === 0) return;
      canvas.width = Math.floor(W * dpr);
      canvas.height = Math.floor(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const lensCenter = () => ({
      x: W * 0.52 + W * DRIFT_X * Math.sin((time * 2 * Math.PI) / DRIFT_SEC_X),
      y:
        H * 0.5 +
        H * DRIFT_Y * Math.sin((time * 2 * Math.PI) / DRIFT_SEC_Y + 1.3),
      r: Math.min(W, H) * LENS_R_FRAC,
    });

    const cellAlpha = (col: number, row: number) =>
      BASE_ALPHA +
      BASE_RANGE * (BAYER[((row % 4) + 4) % 4][((col % 4) + 4) % 4] / 15);

    const drawField = () => {
      // offset the grid so cells straddle the edges (no hard first column)
      for (let col = 0; col * PITCH < W + PITCH; col++) {
        for (let row = 0; row * PITCH < H + PITCH; row++) {
          const x = col * PITCH + PITCH / 2;
          const y = row * PITCH + PITCH / 2;
          ctx.fillStyle = `rgba(${INK},${cellAlpha(col, row)})`;
          ctx.fillRect(x - CUBE / 2, y - CUBE / 2, CUBE, CUBE);
        }
      }
    };

    const sparkEnvelope = (age: number) => {
      if (age < SPARK_IN) return age / SPARK_IN;
      if (age < SPARK_IN + SPARK_HOLD) return 1;
      const out = age - SPARK_IN - SPARK_HOLD;
      return Math.max(0, 1 - out / SPARK_OUT);
    };

    const spawnSpark = (cx: number, cy: number, r: number) => {
      // pick a grid cell well inside the glass so the glow never clips
      const reach = (r * 0.72) / MAG;
      const ang = Math.random() * Math.PI * 2;
      const dist = Math.sqrt(Math.random()) * reach;
      const col = Math.round((cx + Math.cos(ang) * dist - PITCH / 2) / PITCH);
      const row = Math.round((cy + Math.sin(ang) * dist - PITCH / 2) / PITCH);
      sparks.push({
        col,
        row,
        age: 0,
        hue: Math.random() < 0.55 ? "prime" : "sun",
      });
      if (sparks.length > SPARK_MAX) sparks.shift();
    };

    const drawLens = (cx: number, cy: number, r: number) => {
      // magnified field, clipped to the glass
      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.clip();

      ctx.fillStyle = `rgba(${PRIME},${FILL_ALPHA})`;
      ctx.fillRect(cx - r, cy - r, r * 2, r * 2);

      const span = r / MAG + PITCH * 2;
      const colMin = Math.floor((cx - span) / PITCH);
      const colMax = Math.ceil((cx + span) / PITCH);
      const rowMin = Math.floor((cy - span) / PITCH);
      const rowMax = Math.ceil((cy + span) / PITCH);
      const cube = CUBE * MAG;
      for (let col = colMin; col <= colMax; col++) {
        for (let row = rowMin; row <= rowMax; row++) {
          const gx = col * PITCH + PITCH / 2;
          const gy = row * PITCH + PITCH / 2;
          const x = cx + (gx - cx) * MAG;
          const y = cy + (gy - cy) * MAG;
          ctx.fillStyle = `rgba(${INK},${cellAlpha(col, row) * 2.2})`;
          ctx.fillRect(x - cube / 2, y - cube / 2, cube, cube);
        }
      }

      // data points lighting up
      for (const s of sparks) {
        const a = sparkEnvelope(s.age);
        if (a <= 0) continue;
        const gx = s.col * PITCH + PITCH / 2;
        const gy = s.row * PITCH + PITCH / 2;
        const x = cx + (gx - cx) * MAG;
        const y = cy + (gy - cy) * MAG;
        const chan = s.hue === "prime" ? PRIME : SUN;
        const glow = ctx.createRadialGradient(x, y, 0, x, y, SPARK_GLOW_R);
        glow.addColorStop(0, `rgba(${chan},${0.5 * a})`);
        glow.addColorStop(1, `rgba(${chan},0)`);
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(x, y, SPARK_GLOW_R, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = `rgba(${chan},${0.95 * a})`;
        ctx.fillRect(x - cube / 2, y - cube / 2, cube, cube);
      }
      ctx.restore();

      // ring + handle in flat ink
      const ringW = Math.max(3, r * 0.07);
      ctx.strokeStyle = `rgba(${INK},${RING_ALPHA})`;
      ctx.lineWidth = ringW;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.stroke();

      const handleAng = Math.PI * 0.28; // down-right
      const hx = Math.cos(handleAng);
      const hy = Math.sin(handleAng);
      ctx.lineWidth = Math.max(5, r * 0.13);
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.moveTo(cx + hx * (r + ringW / 2), cy + hy * (r + ringW / 2));
      ctx.lineTo(cx + hx * (r * 1.52), cy + hy * (r * 1.52));
      ctx.stroke();
    };

    const frame = (dt: number) => {
      time += dt;
      spawnClock += dt;
      const { x, y, r } = lensCenter();
      if (spawnClock >= SPARK_EVERY) {
        spawnClock = 0;
        spawnSpark(x, y, r);
      }
      sparks = sparks.filter(
        (s) => s.age <= SPARK_IN + SPARK_HOLD + SPARK_OUT,
      );
      for (const s of sparks) s.age += dt;

      ctx.clearRect(0, 0, W, H);
      drawField();
      drawLens(x, y, r);
    };

    const staticFrame = () => {
      ctx.clearRect(0, 0, W, H);
      drawField();
      const { x, y, r } = lensCenter();
      sparks = [];
      for (let i = 0; i < 4; i++) spawnSpark(x, y, r);
      for (const s of sparks) s.age = SPARK_IN; // hold phase: fully lit
      drawLens(x, y, r);
    };

    let raf = 0;
    let active = true;
    let lastT = 0;
    const loop = (now: number) => {
      if (!active) return;
      if (!lastT) lastT = now;
      let dt = (now - lastT) / 1000;
      lastT = now;
      if (dt > 0.05) dt = 0.05;
      frame(dt);
      raf = requestAnimationFrame(loop);
    };

    build();
    if (reduce) {
      staticFrame();
    } else {
      raf = requestAnimationFrame(loop);
    }

    let resizeTimer = 0;
    const ro = new ResizeObserver(() => {
      window.clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(() => {
        build();
        if (reduce) staticFrame();
      }, 180);
    });
    ro.observe(canvas);

    const onVisibility = () => {
      active = !document.hidden;
      if (active && !reduce) {
        lastT = 0;
        raf = requestAnimationFrame(loop);
      }
    };
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      active = false;
      cancelAnimationFrame(raf);
      window.clearTimeout(resizeTimer);
      ro.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [paletteEpoch]);

  return (
    <canvas
      ref={ref}
      aria-hidden
      className={cn("pointer-events-none h-full w-full", className)}
    />
  );
}
