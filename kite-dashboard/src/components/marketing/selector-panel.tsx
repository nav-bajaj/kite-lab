"use client";

import { useState, type ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * Interactive selector panel (clay.com "pick a signal type" reference,
 * design_studies loop 16): pill list on the left, detail surface on the
 * right, caption below. Generic: items carry their own detail ReactNode.
 */
export function SelectorPanel({
  lead,
  items,
  footnote,
  className,
}: {
  lead: string;
  items: { key: string; label: string; detail: ReactNode }[];
  footnote?: ReactNode;
  className?: string;
}) {
  const [active, setActive] = useState(items[0]?.key);
  const current = items.find((i) => i.key === active) ?? items[0];

  return (
    <div
      className={cn(
        "rounded-[28px] bg-[color-mix(in_oklab,var(--foreground)_3.5%,var(--card))] p-6 sm:p-9",
        className,
      )}
    >
      <p className="text-lg font-semibold tracking-[-0.01em] text-foreground">
        {lead}
      </p>
      <div className="mt-6 grid gap-5 lg:grid-cols-[0.4fr_1fr]">
        <div className="flex flex-col gap-2.5" role="tablist" aria-label={lead}>
          {items.map((item) => {
            const selected = item.key === current?.key;
            return (
              <button
                key={item.key}
                type="button"
                role="tab"
                aria-selected={selected}
                onClick={() => setActive(item.key)}
                className={cn(
                  "rounded-full px-5 py-3 text-left text-[15px] font-medium transition-colors duration-150",
                  selected
                    ? "bg-foreground text-background"
                    : "bg-card text-foreground hover:bg-card/70",
                )}
              >
                {item.label}
              </button>
            );
          })}
        </div>
        <div className="rounded-[20px] bg-card p-6 sm:p-8">{current?.detail}</div>
      </div>
      {footnote ? (
        <p className="mt-6 max-w-[70ch] text-[15px] leading-[1.65] text-muted-foreground">
          {footnote}
        </p>
      ) : null}
    </div>
  );
}

/** Small fact tile for SelectorPanel details. */
export function FactTile({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note?: string;
}) {
  return (
    <div className="rounded-[16px] bg-[color-mix(in_oklab,var(--foreground)_3.5%,var(--card))] p-5">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-1 text-xl font-semibold tracking-[-0.01em] text-foreground">
        {value}
      </p>
      {note ? (
        <p className="mt-2 text-sm leading-[1.5] text-muted-foreground">{note}</p>
      ) : null}
    </div>
  );
}
