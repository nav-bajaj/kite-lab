"use client";

import { useRef, useState } from "react";
import { createPortal } from "react-dom";
import { HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";

/** A small "?" that shows a plain-English explanation on hover/focus. The
 *  tooltip is portaled to <body> so a card's overflow can't clip it. */
export function InfoHint({ text, className }: { text: string; className?: string }) {
  const ref = useRef<HTMLButtonElement>(null);
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);

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
        aria-label="More info"
        onMouseEnter={open}
        onMouseLeave={close}
        onFocus={open}
        onBlur={close}
        className={cn(
          "inline-flex cursor-help items-center text-muted-foreground transition-colors hover:text-foreground",
          className,
        )}
      >
        <HelpCircle className="h-3.5 w-3.5" aria-hidden />
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
            {text}
          </span>,
          document.body,
        )}
    </>
  );
}
