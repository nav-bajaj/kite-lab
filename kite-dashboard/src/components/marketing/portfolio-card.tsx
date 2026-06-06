import type { Universe } from "@/lib/types";

/** Showcase card for one of the production model portfolios on the landing
 *  page. Data comes from src/lib/universes.ts — never hand-typed here. */
export function PortfolioCard({ universe }: { universe: Universe }) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-6">
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">
          {universe.riskProfile}
        </span>
        <span className="font-mono text-sm text-muted-foreground">
          {universe.stocks} stocks
        </span>
      </div>
      <h3 className="font-serif text-xl font-medium leading-[1.2] text-foreground">
        {universe.name}
      </h3>
      <p className="text-[15px] leading-[1.55] text-muted-foreground">
        {universe.description}
      </p>
    </div>
  );
}
