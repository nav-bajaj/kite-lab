"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState, useTransition } from "react";
import { CalendarDays, ChevronDown } from "lucide-react";

/**
 * Quick-jump bar for viewing historical insight snapshots.
 *
 * Combines hand-picked canonical dates (so curious viewers can land
 * on "what did the dashboard read like during COVID?") with a free-form
 * date input. Updates the URL's `date` query param, which the server
 * components on each page read to render that day's data.
 */

const PRESETS: { label: string; date: string }[] = [
  { label: "Latest",           date: "" },
  { label: "2024 election",    date: "2024-06-04" },
  { label: "2023 mid-cap top", date: "2023-12-29" },
  { label: "2022 rate shock",  date: "2022-06-17" },
  { label: "Post-COVID rally", date: "2021-10-15" },
  { label: "COVID crash",      date: "2020-03-23" },
  { label: "2019 election",    date: "2019-05-17" },
  { label: "2018 NBFC crisis", date: "2018-10-05" },
  { label: "2017 melt-up",     date: "2017-10-13" },
];

/** Shared URL-navigation hook for both picker variants. */
function useSnapshotNav() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const currentDate = searchParams.get("date") ?? "";

  function navigate(date: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (date) params.set("date", date);
    else params.delete("date");
    const query = params.toString();
    const url = query ? `${pathname}?${query}` : pathname;
    startTransition(() => router.push(url));
  }

  return { pathname, currentDate, isPending, navigate };
}

/**
 * Compact header variant: a "Snapshot: …" button opening a popover with the
 * same presets + free date input. Lives in the shell header so the
 * time-machine works on every insights page without the full explainer panel.
 */
export function CompactSnapshotPicker() {
  const { pathname, currentDate, isPending, navigate } = useSnapshotNav();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(currentDate);
  const rootRef = useRef<HTMLDivElement | null>(null);

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

  const activePreset = PRESETS.find((p) => p.date === currentDate);
  const label = currentDate
    ? (activePreset?.label ??
      new Date(currentDate).toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
      }))
    : "Latest";

  return (
    <div ref={rootRef} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted"
      >
        <CalendarDays className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
        <span className="text-muted-foreground">Snapshot</span>
        <span>{isPending ? "loading…" : label}</span>
        <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
      </button>
      {open && (
        <div className="absolute right-0 top-full z-30 mt-2 w-72 rounded-xl border border-border bg-popover p-3 shadow-lg">
          <p className="mb-2 text-[11px] leading-[1.5] text-muted-foreground">
            Jump to any trading day back to 2010 — every reading rewinds to how
            it read that day.
          </p>
          <div className="flex flex-wrap gap-1.5">
            {PRESETS.map((p) => (
              <button
                key={p.label}
                onClick={() => {
                  navigate(p.date);
                  setOpen(false);
                }}
                className={
                  "rounded-lg border px-2.5 py-1 text-[11px] font-medium transition-colors " +
                  (currentDate === p.date
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border text-muted-foreground hover:bg-muted hover:text-foreground")
                }
              >
                {p.label}
              </button>
            ))}
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              navigate(draft);
              setOpen(false);
            }}
            className="mt-2 flex items-center gap-1"
          >
            <input
              type="date"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              min="2010-01-04"
              max={new Date().toISOString().slice(0, 10)}
              className="w-full rounded-lg border border-input bg-card px-2.5 py-1 text-xs text-foreground"
            />
            <button
              type="submit"
              className="rounded-lg border border-border px-2.5 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              Go
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

export function SnapshotPicker() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const currentDate = searchParams.get("date") ?? "";
  const [draft, setDraft] = useState(currentDate);

  // Learn pages (explainers + glossary) are evergreen — a "snapshot date"
  // makes no sense there, so hide the picker on that branch.
  if (pathname.startsWith("/insights/learn")) return null;

  function navigate(date: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (date) params.set("date", date);
    else params.delete("date");
    const query = params.toString();
    const url = query ? `${pathname}?${query}` : pathname;
    startTransition(() => router.push(url));
  }

  return (
    <div className="rounded-xl border border-dashed border-border p-5 text-sm">
      <div className="flex items-baseline justify-between gap-3">
        <div className="flex flex-col gap-1">
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Snapshot date · a time machine
          </div>
          <p className="max-w-2xl text-[14px] leading-[1.55] text-foreground">
            Curious what the market looked like during a big moment? Jump to any
            trading day back to 2010 and every reading on this page rewinds to
            show exactly how it read that day. Try the COVID crash or an election
            — it&apos;s the fastest way to get a feel for what &ldquo;calm&rdquo;
            and &ldquo;stressed&rdquo; actually look like.
          </p>
        </div>
        {isPending && (
          <span className="shrink-0 text-xs text-muted-foreground">loading…</span>
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {PRESETS.map((p) => {
          const active = currentDate === p.date;
          return (
            <button
              key={p.label}
              onClick={() => navigate(p.date)}
              className={
                "rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors " +
                (active
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border text-muted-foreground hover:text-foreground hover:bg-muted")
              }
            >
              {p.label}
            </button>
          );
        })}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            navigate(draft);
          }}
          className="ml-2 flex items-center gap-1"
        >
          <input
            type="date"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            min="2010-01-04"
            max={new Date().toISOString().slice(0, 10)}
            className="rounded-lg border border-input bg-card px-3 py-1.5 text-xs text-foreground"
          />
          <button
            type="submit"
            className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            Go
          </button>
        </form>
      </div>
    </div>
  );
}
