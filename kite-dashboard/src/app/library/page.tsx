import { getManifest, groupByPillar } from "@/lib/library";
import { PieceCard } from "@/components/library/PieceCard";

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

export default function LibraryIndex() {
  const manifest = getManifest();
  const groups = groupByPillar(manifest.pieces);

  const orderedPillars = [
    ...PILLAR_ORDER.filter((p) => groups.has(p)),
    ...Array.from(groups.keys()).filter((p) => !PILLAR_ORDER.includes(p)),
  ];

  return (
    <div className="mx-auto w-full max-w-[760px] px-6 py-16 sm:py-20">
      <header className="mb-14 flex flex-col gap-4">
        <span className="text-[13px] font-semibold uppercase tracking-[0.15em] text-primary">
          Marketworks
        </span>
        <h1 className="font-serif text-[2.5rem] font-medium leading-[1.08] tracking-[-0.02em] text-foreground sm:text-5xl">
          Library
        </h1>
        <p className="max-w-[560px] text-lg leading-[1.6] text-muted-foreground">
          Writing on momentum, portfolio construction, and Indian equity
          markets — each piece grounded in our own portfolios and live insight
          engine, not opinions about other people&apos;s books.
        </p>
      </header>

      {manifest.pieces.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-8 text-center text-sm text-muted-foreground">
          <p>No pieces published yet. Check back soon.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-14">
          {orderedPillars.map((pillar) => (
            <section key={pillar}>
              <h2 className="mb-5 text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                {pillar}
              </h2>
              <div className="flex flex-col gap-5">
                {(groups.get(pillar) ?? []).map((piece) => (
                  <PieceCard key={piece.slug} piece={piece} />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
