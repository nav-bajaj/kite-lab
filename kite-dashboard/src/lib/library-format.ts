/** Presentation helpers for /library. */

const FORMAT_LABELS = new Map<string, string>([
  ["snippet", "Snippet"],
  ["daily_take", "Daily take"],
  ["weekly_roundup", "Weekly roundup"],
]);

export function humanizeFormat(format: string): string {
  return (
    FORMAT_LABELS.get(format) ??
    format.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase())
  );
}

export function formatPieceDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

/** Byline for a reading page, e.g.
 *  "By Marketworks · Short article · 7 August 2026 · ~2 min read".
 *  `readingTime` is the piece's `duration` — set for article-shaped pieces
 *  ("~2 min"), empty for legacy pieces; only appended when present. */
export function byline(
  format: string,
  publishedAt: string,
  readingTime?: string
): string {
  const base = `By Marketworks · ${humanizeFormat(format)} · ${formatPieceDate(publishedAt)}`;
  return readingTime ? `${base} · ${readingTime} read` : base;
}
