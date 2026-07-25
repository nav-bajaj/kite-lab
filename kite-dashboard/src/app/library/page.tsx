import { getManifest, groupByPillar } from "@/lib/library";
import { PieceCard } from "@/components/library/PieceCard";

export const metadata = {
  title: "Library — Marketworks",
  description:
    "Marketworks writing on momentum investing, portfolio construction, " +
    "and Indian equity markets. Each piece is grounded in our own portfolios " +
    "and live insight engine — not opinions about other people's books.",
};

// One accent per pillar (six pillars, six accents — DESIGN.md §2.6). The
// heading bar and the cards' format chips share the pillar's accent.
const PILLAR_ACCENTS = [
  { bar: "bg-acc1-line", chip: "border-acc1-line bg-acc1 text-acc1-fg" },
  { bar: "bg-acc2-line", chip: "border-acc2-line bg-acc2 text-acc2-fg" },
  { bar: "bg-acc3-line", chip: "border-acc3-line bg-acc3 text-acc3-fg" },
  { bar: "bg-acc4-line", chip: "border-acc4-line bg-acc4 text-acc4-fg" },
  { bar: "bg-acc5-line", chip: "border-acc5-line bg-acc5 text-acc5-fg" },
  { bar: "bg-acc6-line", chip: "border-acc6-line bg-acc6 text-acc6-fg" },
] as const;

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
          {orderedPillars.map((pillar, pi) => {
            const accent = PILLAR_ACCENTS[pi % PILLAR_ACCENTS.length];
            return (
              <section key={pillar}>
                <h2 className="mb-5 text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  {pillar}
                  <span
                    aria-hidden
                    className={`mt-2 block h-1 w-10 rounded-full ${accent.bar}`}
                  />
                </h2>
                <div className="flex flex-col gap-5">
                  {(groups.get(pillar) ?? []).map((piece) => (
                    <PieceCard
                      key={piece.slug}
                      piece={piece}
                      accentChip={accent.chip}
                    />
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
