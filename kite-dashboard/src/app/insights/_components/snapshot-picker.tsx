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

  function navigate(date: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (date) params.set("date", date);
    else params.delete("date");
    const query = params.toString();
    const url = query ? `${pathname}?${query}` : pathname;
    startTransition(() => router.push(url));
  }

  return (
    <div className="mt-3 rounded border border-dashed border-neutral-300 p-3 text-sm">
      <div className="flex items-baseline justify-between">
        <div className="text-xs uppercase tracking-wide text-neutral-500">
          Snapshot date
        </div>
        {isPending && (
          <span className="text-xs text-neutral-400">loading…</span>
        )}
      </div>

      <div className="mt-2 flex flex-wrap gap-2">
        {PRESETS.map((p) => {
          const active = currentDate === p.date;
          return (
            <button
              key={p.label}
              onClick={() => navigate(p.date)}
              className={
                "rounded border px-2 py-1 text-xs " +
                (active
                  ? "border-neutral-900 bg-neutral-900 text-white"
                  : "border-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-900")
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
            className="rounded border border-neutral-300 px-2 py-1 text-xs"
          />
          <button
            type="submit"
            className="rounded border border-neutral-300 px-2 py-1 text-xs hover:bg-neutral-100 dark:hover:bg-neutral-900"
          >
            Go
          </button>
        </form>
      </div>

      <p className="mt-2 text-xs text-neutral-500">
        Pick a historical date to see what the dashboard read like that day.
        Data goes back to 2010.
      </p>
    </div>
  );
}
