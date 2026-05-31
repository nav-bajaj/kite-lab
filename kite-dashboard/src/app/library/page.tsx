import Link from "next/link";

import { getManifest, groupByPillar } from "@/lib/library";

export const metadata = {
  title: "Library — Marketworks",
  description:
    "Marketworks writing on momentum investing, portfolio construction, " +
    "and Indian equity markets. Each piece is grounded in our own portfolios " +
    "and live insight engine — not opinions about other people's books.",
};

const PILLAR_ORDER = [
  "momentum",
  "portfolio construction",
  "active frameworks",
  "investor mistakes",
  "backtest realism",
  "practical education",
];

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

export default function LibraryIndex() {
  const manifest = getManifest();
  const groups = groupByPillar(manifest.pieces);

  const orderedPillars = [
    ...PILLAR_ORDER.filter((p) => groups.has(p)),
    ...Array.from(groups.keys()).filter((p) => !PILLAR_ORDER.includes(p)),
  ];

  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      <header className="mb-12">
        <h1 className="text-4xl font-semibold tracking-tight">Library</h1>
        <p className="mt-3 max-w-2xl text-base text-neutral-600 dark:text-neutral-400">
          Marketworks writing on momentum, portfolio construction, and Indian
          equity markets. Each piece is grounded in our own portfolios and
          insight engine.
        </p>
      </header>

      {manifest.pieces.length === 0 ? (
        <div className="rounded-md border border-neutral-200 bg-neutral-50 p-8 text-center text-sm text-neutral-600 dark:border-neutral-800 dark:bg-neutral-900 dark:text-neutral-400">
          <p>No pieces published yet. Check back soon.</p>
        </div>
      ) : (
        <div className="space-y-12">
          {orderedPillars.map((pillar) => (
            <section key={pillar}>
              <h2 className="mb-4 text-sm font-medium uppercase tracking-wider text-neutral-500 dark:text-neutral-400">
                {pillar}
              </h2>
              <ul className="space-y-6">
                {(groups.get(pillar) ?? []).map((piece) => (
                  <li key={piece.slug}>
                    <Link
                      href={`/library/${piece.slug}`}
                      className="group block rounded-lg border border-neutral-200 p-6 transition hover:border-neutral-400 dark:border-neutral-800 dark:hover:border-neutral-600"
                    >
                      <div className="flex items-baseline justify-between gap-4">
                        <h3 className="text-xl font-medium tracking-tight group-hover:underline">
                          {piece.title}
                        </h3>
                        <time className="shrink-0 text-xs text-neutral-500 dark:text-neutral-500">
                          {formatDate(piece.published_at)}
                        </time>
                      </div>
                      {piece.hook && (
                        <p className="mt-3 text-sm text-neutral-700 dark:text-neutral-300">
                          {piece.hook}
                        </p>
                      )}
                      <p className="mt-3 text-xs uppercase tracking-wider text-neutral-500 dark:text-neutral-500">
                        {piece.format}
                      </p>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
