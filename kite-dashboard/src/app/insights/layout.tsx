import { Suspense } from "react";
import { SnapshotPicker } from "./_components/snapshot-picker";
import { InsightsTabs } from "@/components/insights/tabs";

export const metadata = {
  title: "Insights — Marketworks",
  description:
    "Quantitative market commentary on Indian equities — regime, stress, sector rotation, and historical analogs.",
};

export default function InsightsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mw-app min-h-screen bg-background">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <header className="flex flex-col gap-5 border-b border-border pb-6">
          <div className="flex flex-col gap-2">
            <span className="text-[13px] font-semibold uppercase tracking-[0.15em] text-primary">
              Marketworks
            </span>
            <h1 className="font-serif text-[2rem] font-medium tracking-[-0.02em] text-foreground">
              Insights
            </h1>
            <p className="max-w-2xl text-[15px] leading-[1.6] text-muted-foreground">
              A daily quantitative read on Indian equity markets — regime,
              stress, sector rotation, and cross-asset context. Educational;
              not investment advice.
            </p>
          </div>
          <InsightsTabs />
          <Suspense fallback={null}>
            <SnapshotPicker />
          </Suspense>
        </header>

        <div className="py-8">{children}</div>

        <footer className="mt-8 border-t border-border pt-6 text-[13px] text-muted-foreground">
          Educational commentary based on quantitative market data — not
          investment advice. Past patterns do not guarantee future outcomes.
        </footer>
      </div>
    </div>
  );
}
