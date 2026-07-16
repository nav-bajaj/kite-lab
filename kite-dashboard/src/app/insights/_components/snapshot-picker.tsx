"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { useState, useTransition } from "react";

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
