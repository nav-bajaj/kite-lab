"use client";

import { useEffect, useRef } from "react";

import { cn } from "@/lib/utils";

/**
 * Canvas dot field for the marketing base (homepage_visual_refresh).
 *
 * A viewport-fixed grid of lichen dots: clearly visible and calm through the
 * centre, with individual dots pulsing (growing + brightening on their own
 * random timers) more and more toward the edges — a gentle autonomous twinkle,
 * NOT tied to scroll. Sits at z-0 behind the page content; the solid panels
 * cover it, so it reads only in the near-white base. Under prefers-reduced-
 * motion it draws once, static. Purely decorative (aria-hidden).
 */
const LICHEN = "20,113,95";
const GAP = 26; // dot pitch (px)

type Dot = { x: number; y: number; edge: number; phase: number; speed: number; pulses: boolean };

export function FlowDots({ className }: { className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    let W = 0;
    let H = 0;
    let dots: Dot[] = [];

    const build = () => {
      W = window.innerWidth;
      H = window.innerHeight;
      canvas.width = Math.floor(W * dpr);
      canvas.height = Math.floor(H * dpr);
      canvas.style.width = `${W}px`;
      canvas.style.height = `${H}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      dots = [];
      for (let y = GAP / 2; y < H; y += GAP) {
        for (let x = GAP / 2; x < W; x += GAP) {
          const ex = Math.abs(x - W / 2) / (W / 2);
          const ey = Math.abs(y - H / 2) / (H / 2);
          const edge = Math.min(1, Math.max(ex, ey)); // 0 centre -> 1 edge
          dots.push({
            x,
            y,
            edge,
            phase: Math.random() * Math.PI * 2,
            speed: 0.5 + Math.random() * 1.1,
            // more dots pulse toward the edges; a few sprinkle through the middle
            pulses: Math.random() < 0.12 + edge * 0.55,
          });
        }
      }
    };

    const draw = (t: number) => {
      ctx.clearRect(0, 0, W, H);
      for (const d of dots) {
        let r = 1.3;
        // calmer through the centre (behind copy), stronger toward the edges
        let a = 0.1 + d.edge * 0.08;
        if (!reduce && d.pulses) {
          const p = (Math.sin(t * d.speed + d.phase) + 1) / 2; // 0..1
          const strength = 0.25 + d.edge * 0.75; // edges pulse hardest
          r += p * 2.6 * strength;
          a += p * 0.34 * strength;
        }
        ctx.beginPath();
        ctx.arc(d.x, d.y, r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${LICHEN},${a})`;
        ctx.fill();
      }
    };

    let raf = 0;
    let t = 0;
    let active = true;
    const frame = () => {
      if (!active) return;
      t += 0.018;
      draw(t);
      raf = requestAnimationFrame(frame);
    };

    build();
    if (reduce) {
      draw(0);
    } else {
      raf = requestAnimationFrame(frame);
    }

    let resizeTimer = 0;
    const onResize = () => {
      window.clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(() => {
        build();
        if (reduce) draw(0);
      }, 150);
    };
    const onVisibility = () => {
      active = !document.hidden;
      if (active && !reduce) raf = requestAnimationFrame(frame);
    };
    window.addEventListener("resize", onResize);
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      active = false;
      cancelAnimationFrame(raf);
      window.clearTimeout(resizeTimer);
      window.removeEventListener("resize", onResize);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  return (
    <canvas
      ref={ref}
      aria-hidden
      className={cn("pointer-events-none fixed inset-0 z-0", className)}
    />
  );
}
