"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ChevronDown, Layers } from "lucide-react";
import { BREADTH_UNIVERSES, parseUniverse, universeLabel } from "@/lib/insights-api";

/**
 * Universe scope selector (top bar, next to the snapshot picker). Sets the
 * `?universe=` URL param that the breadth-family pages read. Nifty 500 is
 * the default and keeps the URL clean; market-wide indicators (VIX, stress,
 * concentration) are unaffected by design.
 */
export function UniverseSelector() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const current = parseUniverse(searchParams.get("universe") ?? undefined);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: PointerEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    window.addEventListener("pointerdown", onPointerDown);
    return () => window.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  if (pathname.startsWith("/insights/learn")) return null;

  function select(id: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (id === "nse500") params.delete("universe");
    else params.set("universe", id);
    const query = params.toString();
    startTransition(() => router.push(query ? `${pathname}?${query}` : pathname));
    setOpen(false);
  }

  return (
    <div ref={rootRef} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted"
      >
        <Layers className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
        <span className="text-muted-foreground">Universe</span>
        <span>{isPending ? "loading…" : universeLabel(current)}</span>
        <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
      </button>
      {open && (
        <div className="absolute right-0 top-full z-30 mt-2 w-44 rounded-xl border border-border bg-popover p-1.5 shadow-lg">
          {BREADTH_UNIVERSES.map((u) => (
            <button
              key={u.id}
              onClick={() => select(u.id)}
              className={
                "block w-full rounded-lg px-3 py-1.5 text-left text-xs font-medium transition-colors " +
                (u.id === current
                  ? "bg-primary text-primary-foreground"
                  : "text-foreground hover:bg-muted")
              }
            >
              {u.label}
            </button>
          ))}
          <p className="px-3 pb-1 pt-1.5 text-[10px] leading-[1.4] text-muted-foreground">
            Scopes breadth metrics. Market-wide gauges (VIX, stress) are
            unaffected.
          </p>
        </div>
      )}
    </div>
  );
}
