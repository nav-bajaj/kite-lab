"use client";

import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

/* eslint-disable security/detect-object-injection --
 * Decorative canvas: every bracket access below is a numeric index into a local
 * array (curve samples / anchor points), never a user-controlled key, so the
 * object-injection rule is a false positive throughout this file. */

/**
 * Hero flow animation (homepage_visual_refresh).
 *
 * The brand story as ambient motion: many symmetric "market signals" drift in
 * from the left carrying soft pulses, converge on a slowly breathing central
 * node, and are transformed into one dramatic portfolio curve that grows
 * up-and-right with a halftone-shaded area. Scoped to its parent (the hero
 * section) and transparent — the page-wide FlowGrid shows through underneath.
 * Autonomous (not scroll-driven); static under reduced-motion; pauses on hidden
 * tab. Purely decorative (aria-hidden). Palette-exact colours: the two
 * channel strings are resolved from --primary/--secondary at mount and
 * re-resolved when the palette changes (canvas can't consume CSS vars).
 */

// Resolved at runtime from the palette tokens; Mint values as SSR-safe
// fallbacks. Module-level because the draw closures template them per frame.
let LICHEN = "12,122,98"; // --primary fallback (#0C7A62)
let SIGNAL = "85,195,116"; // --secondary fallback (#55C374)

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

function resolveFlowColors(el: HTMLElement) {
  const cs = getComputedStyle(el);
  LICHEN = cssColorToChannels(cs.getPropertyValue("--primary")) ?? LICHEN;
  SIGNAL = cssColorToChannels(cs.getPropertyValue("--secondary")) ?? SIGNAL;
}

// ---- convergence node (fraction of the hero box) ----
const NODE_X = 0.5;
const NODE_Y = 0.5;

// ---- symmetric source lines ----
const SOURCE_PAIRS = 6; // 12 lines
const SOURCE_SPREAD = 0.4;
const SOURCE_CENTER_GAP = 0.11;
const SOURCE_ALPHA = 0.08;
const SOURCE_WIDTH = 1.0;
const SOURCE_START_X = -0.02;
const SOURCE_CURVE = 0.55;

// ---- pulses lead; each source fires ONE comet head that draws its line behind it ----
const PULSE_DUR = 4.0; // travel from the left edge to the node
const PAIR_STAGGER = 0.4; // delay between successive mirrored pairs (rolling wave)
const PULSE_CORE_R = 2.2;
const PULSE_GLOW_R = 11.0;
const PULSE_ALPHA = 0.7;

// ---- node (slow breathing) ----
const NODE_BASE_R = 32;
const NODE_BASE_ALPHA = 0.12;
const NODE_BREATH_SEC = 4.6;
const NODE_BREATH_AMT = 0.38;
const NODE_FLARE_R = 16;
const NODE_FLARE_GAIN = 0.11;
const NODE_FLARE_DECAY = 0.6;

// ---- single, slow loop: lines trace in (left) -> growth out (right) -> fade -> repeat ----
const LOOP_SEC = 14.5; // full cycle length
const FADE_IN_SEC = 0.8; // scene eases in at the start of each loop
const FADE_OUT_SEC = 1.5; // scene fades out at the end
const GAP_SEC = 0.2; // brief blank beat before it begins again

// ---- portfolio growth line (begins when the FIRST pulse lands) ----
const GROW_DRAW_SEC = 8.0; // growth draw duration
const GROW_END_X = 1.0;
const GROW_RISE = 0.4;
const GROW_WIDTH = 2.0;
const GROW_TAIL_FADE = 0.65;
const GROW_DOT_R = 3.4;
const GROW_DOT_GLOW_R = 15;
const GROW_SEG = 200;
const GROW_FILL_BASE = 0.06;
const GROW_HALFTONE_A = 0.62;
const GROW_FILL_FLOOR = 0.28;
const HALFTONE_TILE = 7;
const HALFTONE_DOT_R = 1.15;

// curvy, dramatic shape: [progressX, heightFraction] anchors (Catmull-Rom)
const GROW_ANCHORS: [number, number][] = [
  [0.0, 0.0],
  [0.16, 0.11],
  [0.32, 0.07],
  [0.5, 0.33],
  [0.64, 0.28],
  [0.8, 0.6],
  [0.91, 0.75],
  [1.0, 1.0],
];

type Source = {
  startX: number;
  startY: number;
  ctrlX: number;
  ctrlY: number;
  endX: number;
  endY: number;
  delay: number; // when this source's comet begins (staggered wave)
  u: number; // 0..1 progress of the comet toward the node
  landed: boolean; // has it reached the node yet
};

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}
function easeInOutSine(t: number) {
  return 0.5 - 0.5 * Math.cos(Math.PI * t);
}
function catmull(p0: number, p1: number, p2: number, p3: number, t: number) {
  const t2 = t * t;
  const t3 = t2 * t;
  return (
    0.5 *
    (2 * p1 +
      (-p0 + p2) * t +
      (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
      (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
  );
}
function growthValue(g: number) {
  const A = GROW_ANCHORS;
  const n = A.length;
  if (g <= A[0][0]) return A[0][1];
  if (g >= A[n - 1][0]) return A[n - 1][1];
  let i = 0;
  while (i < n - 1 && A[i + 1][0] < g) i++;
  const p1 = A[i];
  const p2 = A[i + 1];
  const p0 = A[i - 1] || p1;
  const p3 = A[i + 2] || p2;
  const u = (g - p1[0]) / (p2[0] - p1[0]);
  return catmull(p0[1], p1[1], p2[1], p3[1], u);
}

export function HeroFlow({ className }: { className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null);
  // Bumped when the palette (class / data-palette on <html>) changes so the
  // main effect re-inits with re-resolved colors + a rebuilt halftone pattern.
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

    resolveFlowColors(canvas);

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let W = 0;
    let H = 0;
    let dpr = 1;
    let sources: Source[] = [];
    const node = { x: 0, y: 0, flare: 0 };
    let growthPath: { x: number; y: number }[] = [];
    let halftone: CanvasPattern | null = null;
    let time = 0;
    let loopClock = 0;
    let firstLanded = false;
    let growthStart = 0;

    const makeHalftone = () => {
      const pc = document.createElement("canvas");
      pc.width = HALFTONE_TILE;
      pc.height = HALFTONE_TILE;
      const p = pc.getContext("2d");
      if (!p) return null;
      p.fillStyle = `rgba(${LICHEN},0.62)`;
      p.beginPath();
      p.arc(HALFTONE_TILE / 2, HALFTONE_TILE / 2, HALFTONE_DOT_R, 0, Math.PI * 2);
      p.fill();
      return ctx.createPattern(pc, "repeat");
    };

    const buildSources = () => {
      sources = [];
      for (let k = 0; k < SOURCE_PAIRS; k++) {
        const frac = k / Math.max(1, SOURCE_PAIRS - 1);
        const offset = lerp(SOURCE_CENTER_GAP, SOURCE_SPREAD, frac);
        const delay = k * PAIR_STAGGER; // mirrored pair shares a delay -> rolling wave
        for (const sign of [-1, 1]) {
          const startX = SOURCE_START_X * W;
          const startY = (NODE_Y + sign * offset) * H;
          sources.push({
            startX,
            startY,
            ctrlX: lerp(startX, node.x, SOURCE_CURVE),
            ctrlY: startY,
            endX: node.x,
            endY: node.y,
            delay,
            u: 0,
            landed: false,
          });
        }
      }
    };

    const buildGrowthPath = () => {
      growthPath = [];
      const x0 = node.x;
      const y0 = node.y;
      const x1 = GROW_END_X * W;
      const rise = GROW_RISE * H;
      for (let i = 0; i <= GROW_SEG; i++) {
        const t = i / GROW_SEG;
        growthPath.push({ x: lerp(x0, x1, t), y: y0 - growthValue(t) * rise });
      }
    };

    const build = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = canvas.clientWidth;
      H = canvas.clientHeight;
      if (W === 0 || H === 0) return;
      canvas.width = Math.floor(W * dpr);
      canvas.height = Math.floor(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      node.x = NODE_X * W;
      node.y = NODE_Y * H;
      node.flare = 0;
      halftone = makeHalftone();
      buildSources();
      buildGrowthPath();
    };

    const sourcePoint = (s: Source, u: number) => {
      const mu = 1 - u;
      return {
        x: mu * mu * s.startX + 2 * mu * u * s.ctrlX + u * u * s.endX,
        y: mu * mu * s.startY + 2 * mu * u * s.ctrlY + u * u * s.endY,
      };
    };

    // draw the source line only up to the comet head (uHead) — line trails behind the pulse
    const drawSourceTrail = (s: Source, uHead: number, env: number) => {
      if (uHead <= 0) return;
      const steps = 24;
      ctx.beginPath();
      ctx.moveTo(s.startX, s.startY);
      for (let i = 1; i <= steps; i++) {
        const p = sourcePoint(s, (i / steps) * uHead);
        ctx.lineTo(p.x, p.y);
      }
      ctx.strokeStyle = `rgba(${LICHEN},${SOURCE_ALPHA * env})`;
      ctx.lineWidth = SOURCE_WIDTH;
      ctx.stroke();
    };

    const drawPulse = (x: number, y: number, bright: number) => {
      const g = ctx.createRadialGradient(x, y, 0, x, y, PULSE_GLOW_R);
      g.addColorStop(0, `rgba(${SIGNAL},${0.4 * bright})`);
      g.addColorStop(1, `rgba(${SIGNAL},0)`);
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(x, y, PULSE_GLOW_R, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = `rgba(${SIGNAL},${PULSE_ALPHA * bright})`;
      ctx.beginPath();
      ctx.arc(x, y, PULSE_CORE_R, 0, Math.PI * 2);
      ctx.fill();
    };

    const drawNode = (env: number) => {
      const breath = 0.5 + 0.5 * Math.sin((time * 2 * Math.PI) / NODE_BREATH_SEC);
      const bMul = 1 + NODE_BREATH_AMT * breath;
      const r = NODE_BASE_R * bMul + node.flare * NODE_FLARE_R;
      const a = (NODE_BASE_ALPHA * bMul + node.flare * NODE_FLARE_GAIN) * env;
      const g = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, r);
      g.addColorStop(0, `rgba(${SIGNAL},${a})`);
      g.addColorStop(0.5, `rgba(${LICHEN},${a * 0.5})`);
      g.addColorStop(1, `rgba(${LICHEN},0)`);
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
      ctx.fill();
    };

    const drawGrowth = (prog: number, alpha: number) => {
      const n = growthPath.length;
      const f = prog * (n - 1);
      const last = Math.max(0, Math.min(n - 2, Math.floor(f)));
      const frac = f - last;
      const a0 = growthPath[last];
      const a1 = growthPath[last + 1];
      const tip = { x: lerp(a0.x, a1.x, frac), y: lerp(a0.y, a1.y, frac) };

      let minY = node.y;
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(growthPath[0].x, node.y);
      for (let i = 0; i <= last; i++) {
        ctx.lineTo(growthPath[i].x, growthPath[i].y);
        if (growthPath[i].y < minY) minY = growthPath[i].y;
      }
      ctx.lineTo(tip.x, tip.y);
      if (tip.y < minY) minY = tip.y;
      ctx.lineTo(tip.x, node.y);
      ctx.closePath();

      ctx.fillStyle = `rgba(${LICHEN},${GROW_FILL_BASE * alpha})`;
      ctx.fill();

      if (halftone) {
        ctx.clip();
        ctx.globalAlpha = GROW_HALFTONE_A * alpha;
        ctx.fillStyle = halftone;
        ctx.fillRect(0, 0, W, H);
        ctx.globalAlpha = 1;
        ctx.globalCompositeOperation = "destination-in";
        const grad = ctx.createLinearGradient(0, minY, 0, node.y);
        grad.addColorStop(0, "rgba(0,0,0,1)");
        grad.addColorStop(1, `rgba(0,0,0,${GROW_FILL_FLOOR})`);
        ctx.fillStyle = grad;
        ctx.fillRect(0, minY, W, node.y - minY + 1);
      }
      ctx.restore();

      ctx.lineWidth = GROW_WIDTH;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      const drawSeg = (
        x1: number,
        y1: number,
        x2: number,
        y2: number,
        tt: number,
      ) => {
        const tail = lerp(GROW_TAIL_FADE, 1, tt);
        ctx.strokeStyle = `rgba(${LICHEN},${alpha * tail})`;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      };
      for (let i = 1; i <= last; i++) {
        drawSeg(
          growthPath[i - 1].x,
          growthPath[i - 1].y,
          growthPath[i].x,
          growthPath[i].y,
          i / (n - 1),
        );
      }
      drawSeg(growthPath[last].x, growthPath[last].y, tip.x, tip.y, prog);

      const gg = ctx.createRadialGradient(tip.x, tip.y, 0, tip.x, tip.y, GROW_DOT_GLOW_R);
      gg.addColorStop(0, `rgba(${SIGNAL},${0.55 * alpha})`);
      gg.addColorStop(1, `rgba(${SIGNAL},0)`);
      ctx.fillStyle = gg;
      ctx.beginPath();
      ctx.arc(tip.x, tip.y, GROW_DOT_GLOW_R, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = `rgba(${SIGNAL},${0.95 * alpha})`;
      ctx.beginPath();
      ctx.arc(tip.x, tip.y, GROW_DOT_R, 0, Math.PI * 2);
      ctx.fill();
    };

    // whole-scene fade: ease in at loop start, hold, fade out, brief blank gap
    const envelope = (tc: number) => {
      if (tc < FADE_IN_SEC) return tc / FADE_IN_SEC;
      const fadeEnd = LOOP_SEC - GAP_SEC;
      const fadeStart = fadeEnd - FADE_OUT_SEC;
      if (tc >= fadeEnd) return 0;
      if (tc > fadeStart) return (fadeEnd - tc) / FADE_OUT_SEC;
      return 1;
    };

    const frame = (dt: number) => {
      time += dt;
      loopClock += dt;
      if (loopClock >= LOOP_SEC) {
        loopClock = 0;
        firstLanded = false;
        growthStart = 0;
        for (const s of sources) {
          s.u = 0;
          s.landed = false;
        }
      }
      const env = envelope(loopClock);

      ctx.clearRect(0, 0, W, H);
      node.flare = Math.max(0, node.flare - NODE_FLARE_DECAY * dt);

      // advance each comet and draw its line trailing behind the head
      for (const s of sources) {
        if (loopClock >= s.delay && s.u < 1) {
          s.u = Math.min(1, s.u + dt / PULSE_DUR);
          if (s.u >= 1 && !s.landed) {
            s.landed = true;
            node.flare = Math.min(1, node.flare + NODE_FLARE_GAIN);
            if (!firstLanded) {
              firstLanded = true;
              growthStart = loopClock;
            }
          }
        }
        if (loopClock >= s.delay) {
          drawSourceTrail(s, easeInOutSine(s.u), env);
        }
      }

      drawNode(env);

      // bright comet head while the pulse is still travelling
      for (const s of sources) {
        if (loopClock >= s.delay && !s.landed) {
          const uHead = easeInOutSine(s.u);
          const pt = sourcePoint(s, uHead);
          drawPulse(pt.x, pt.y, (0.5 + 0.5 * uHead) * env);
        }
      }

      // growth begins the moment the first pulse lands
      if (firstLanded) {
        const prog = easeInOutSine(
          Math.min(1, (loopClock - growthStart) / GROW_DRAW_SEC),
        );
        if (prog > 0) drawGrowth(prog, env);
      }
    };

    const staticFrame = () => {
      ctx.clearRect(0, 0, W, H);
      for (const s of sources) drawSourceTrail(s, 1, 1);
      drawNode(1);
      drawGrowth(1, 1);
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
