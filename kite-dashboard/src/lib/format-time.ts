/**
 * Succinct, ops-friendly job timestamps, pinned to IST so they always line
 * up with the market clock (15:30 close, 16:30 pipeline) no matter where
 * the viewer is.
 *
 *   < 1 min   -> "just now"
 *   < 60 min  -> "18m ago"
 *   same day  -> "Today 22:17"
 *   prev day  -> "Yesterday 16:30"
 *   older     -> "Jul 11, 16:00"  (year appended when it differs)
 */

const IST = "Asia/Kolkata";

/** Backend job timestamps are UTC; treat a naive ISO string as UTC rather
 * than letting `new Date()` guess browser-local. */
function parseUtc(iso: string): Date {
  const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/.test(iso);
  return new Date(hasZone ? iso : `${iso}Z`);
}

function istDayKey(d: Date): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: IST,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(d);
}

function istTime(d: Date): string {
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: IST,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(d);
}

export function formatJobTime(iso: string, now: Date = new Date()): string {
  const d = parseUtc(iso);
  if (isNaN(d.getTime())) return iso;

  const mins = Math.round((now.getTime() - d.getTime()) / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;

  const dayKey = istDayKey(d);
  const todayKey = istDayKey(now);
  if (dayKey === todayKey) return `Today ${istTime(d)}`;
  if (dayKey === istDayKey(new Date(now.getTime() - 86_400_000))) {
    return `Yesterday ${istTime(d)}`;
  }

  const sameYear = dayKey.slice(0, 4) === todayKey.slice(0, 4);
  const monthDay = new Intl.DateTimeFormat("en-US", {
    timeZone: IST,
    month: "short",
    day: "numeric",
    ...(sameYear ? {} : { year: "numeric" }),
  }).format(d);
  return `${monthDay}, ${istTime(d)}`;
}

/** Full detail for tooltips: "14 Jul 2026, 22:17:59 IST". */
export function formatJobTimeFull(iso: string): string {
  const d = parseUtc(iso);
  if (isNaN(d.getTime())) return iso;
  const s = new Intl.DateTimeFormat("en-GB", {
    timeZone: IST,
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(d);
  return `${s} IST`;
}
