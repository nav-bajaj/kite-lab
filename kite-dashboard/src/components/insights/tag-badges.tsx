"use client";

import { useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  ArrowUpToLine,
  BarChart2,
  Crown,
  Maximize2,
  Minimize2,
  Moon,
  Rocket,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { badgeToneClass, Tag, type Tone } from "./ui";

// Compact icon badge per engine insight-tag. The full plain-English meaning
// shows in a hover/focus tooltip (portaled to <body> so the table's horizontal
// scroll container can't clip it). Icons/descriptions map 1:1 to the engine
// tags — never invent a tag or imply an action.
type Meta = { icon: LucideIcon; desc: string; tone: Tone };

const TAG_META = new Map<string, Meta>([
  ["Momentum leader", { icon: Crown, tone: "positive", desc: "Momentum leader — among the strongest-ranked stocks in the market." }],
  ["Near 52-week high", { icon: ArrowUpToLine, tone: "positive", desc: "Near its 52-week high — trading close to its highest price in a year." }],
  ["Fresh 52-week high", { icon: Sparkles, tone: "positive", desc: "Fresh 52-week high — just made a new one-year high." }],
  ["Volume expansion", { icon: BarChart2, tone: "default", desc: "Volume expansion — trading on notably heavier volume than usual." }],
  ["Extended", { icon: Maximize2, tone: "warning", desc: "Extended — stretched well above its moving averages. A state, not a sell signal." }],
  ["Coiled", { icon: Minimize2, tone: "default", desc: "Coiled — trading in a tight range, often before a bigger move." }],
  ["New momentum", { icon: Rocket, tone: "positive", desc: "New momentum — climbing fast up the strength ranking recently." }],
  ["Quiet", { icon: Moon, tone: "default", desc: "Quiet — a steady, low-drama uptrend rather than a sharp spike." }],
]);

function TagBadge({ tag, meta }: { tag: string; meta: Meta }) {
  const ref = useRef<HTMLButtonElement>(null);
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);
  const Icon = meta.icon;

  const open = () => {
    const r = ref.current?.getBoundingClientRect();
    if (r) setPos({ x: r.left + r.width / 2, y: r.top });
  };
  const close = () => setPos(null);

  return (
    <>
      <button
        ref={ref}
        type="button"
        aria-label={tag}
        onMouseEnter={open}
        onMouseLeave={close}
        onFocus={open}
        onBlur={close}
        className={cn(
          "inline-flex h-5 w-5 cursor-help items-center justify-center rounded-md border bg-card outline-none focus-visible:ring-2 focus-visible:ring-ring",
          badgeToneClass(meta.tone),
        )}
      >
        <Icon className="h-3 w-3" strokeWidth={2} aria-hidden />
      </button>
      {pos &&
        typeof document !== "undefined" &&
        createPortal(
          <span
            role="tooltip"
            style={{
              position: "fixed",
              left: pos.x,
              top: pos.y - 8,
              transform: "translate(-50%, -100%)",
            }}
            className="pointer-events-none z-[100] max-w-[240px] rounded-md bg-foreground px-2.5 py-1.5 text-[12px] leading-[1.4] text-background shadow-lg"
          >
            {meta.desc}
          </span>,
          document.body,
        )}
    </>
  );
}

/** Row of insight-tag icon badges with hover/focus tooltips. Unknown tags fall
 *  back to a text pill. */
export function TagBadges({ tags }: { tags: string[] }) {
  if (!tags.length) return null;
  return (
    <div className="flex flex-wrap items-center gap-1">
      {tags.map((t) => {
        const meta = TAG_META.get(t);
        if (!meta) return <Tag key={t} label={t} />;
        return <TagBadge key={t} tag={t} meta={meta} />;
      })}
    </div>
  );
}
