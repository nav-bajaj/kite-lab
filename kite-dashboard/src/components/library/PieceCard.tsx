import Link from "next/link";

import type { LibraryManifestEntry } from "@/lib/library";
import { formatPieceDate, humanizeFormat } from "@/lib/library-format";

/** A single piece in the /library index list. `accentChip` (optional) renders
 *  the format label as an accent-rotation chip — the index passes the parent
 *  pillar's accent so cards inherit their section's identity (DESIGN.md §2.6). */
export function PieceCard({
  piece,
  accentChip,
}: {
  piece: LibraryManifestEntry;
  accentChip?: string;
}) {
  return (
    <Link
      href={`/library/${piece.slug}`}
      className="group flex flex-col gap-3 rounded-xl border border-border bg-card p-6 transition-colors hover:border-primary/40"
    >
      <div className="flex items-baseline justify-between gap-4">
        <span
          className={
            accentChip
              ? `rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.14em] ${accentChip}`
              : "text-xs font-semibold uppercase tracking-[0.14em] text-primary"
          }
        >
          {humanizeFormat(piece.format)}
        </span>
        <time className="shrink-0 text-xs text-muted-foreground">
          {formatPieceDate(piece.published_at)}
        </time>
      </div>
      <h3 className="font-serif text-2xl font-medium leading-[1.2] tracking-[-0.01em] text-foreground">
        {piece.title}
      </h3>
      {piece.hook && (
        <p className="text-[15px] leading-[1.55] text-muted-foreground">
          {piece.hook}
        </p>
      )}
    </Link>
  );
}
