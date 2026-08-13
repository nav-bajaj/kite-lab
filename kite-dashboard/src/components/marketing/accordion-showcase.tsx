"use client";

/* design_studies loop 28 (B-h, PERCEPT P5): synced accordion + visual.
 * One item open at a time; the visual panel swaps with a short
 * crossfade. Real product facts only; visuals are TexturePanel
 * variants until real screenshots exist. */

import { useState } from "react";

import { TexturePanel, type TextureVariant } from "./composition-primitives";

type Item = {
  title: string;
  body: string;
  visual: TextureVariant;
  chip: string;
};

const ITEMS: Item[] = [
  {
    title: "Weekly scoring",
    body: "The system scores the whole NSE 500 every week and ranks it by momentum. No headlines, no hunches.",
    visual: "grid",
    chip: "499 names scored",
  },
  {
    title: "Fixed-cadence rebalance",
    body: "Portfolios rebuild on a fixed calendar - weekly or bi-weekly - around the current leaders.",
    visual: "dither",
    chip: "rebuilt on schedule",
  },
  {
    title: "Written risk controls",
    body: "A 20% drawdown stop checked weekly, equal 1/N sizing, and a 7.5% cap per position. The exits are written before the entries.",
    visual: "dots",
    chip: "20% stop · 1/N · 7.5% cap",
  },
];

export function AccordionShowcase({ className = "" }: { className?: string }) {
  const [open, setOpen] = useState(0);
  const active = ITEMS.at(open) ?? ITEMS.at(0)!;
  return (
    <div className={`grid gap-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)] ${className}`}>
      <div>
        {ITEMS.map((item, i) => {
          const isOpen = i === open;
          return (
            <div key={item.title} className="border-b border-border">
              <button
                type="button"
                aria-expanded={isOpen}
                onClick={() => setOpen(i)}
                className="flex w-full items-center justify-between gap-4 py-5 text-left"
              >
                <span
                  className={`text-lg font-semibold ${isOpen ? "text-foreground" : "text-muted-foreground"}`}
                >
                  {item.title}
                </span>
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 14 14"
                  aria-hidden
                  className={`shrink-0 transition-transform duration-200 ${isOpen ? "rotate-45" : ""}`}
                >
                  <path
                    d="M7 1v12M1 7h12"
                    className="stroke-[var(--primary)]"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />
                </svg>
              </button>
              <div
                className={`grid transition-[grid-template-rows] duration-200 ease-out ${
                  isOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
                }`}
              >
                <div className="overflow-hidden">
                  <p className="pb-5 pr-8 text-[15px] leading-[1.65] text-muted-foreground">
                    {item.body}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div
        key={active.title}
        className="relative min-h-[320px] overflow-hidden rounded-[20px] border border-border/60 bg-card mw-fade-in"
      >
        <TexturePanel variant={active.visual} />
        <div className="absolute bottom-6 left-6 right-6 rounded-[12px] border border-border bg-background/90 px-5 py-4 backdrop-blur-sm">
          <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-acc1-fg">
            {active.chip}
          </p>
          <p className="mt-1.5 text-sm font-medium text-foreground">
            {active.title}
          </p>
        </div>
      </div>
    </div>
  );
}
