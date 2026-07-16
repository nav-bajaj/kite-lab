import { Suspense } from "react";
import { SnapshotPicker } from "./_components/snapshot-picker";
import { InsightsTabs } from "@/components/insights/tabs";
import { MarketingNav } from "@/components/marketing/marketing-nav";
import { MarketingFooter } from "@/components/marketing/marketing-footer";

export const metadata = {
  title: "Insights — Marketworks",
  description:
    "A simple daily read on Indian markets — trend, stress, sector leaders, and a screener that scores every stock the way our portfolios do.",
};

export default function InsightsLayout({ children }: { children: React.ReactNode }) {
  return (
    // `.mw-app` (not `.mw-brand`) so the finance up/down colours resolve, while
    // MarketingNav + MarketingFooter give Insights the same site chrome as the
    // rest of the marketing surfaces (landing, /portfolios, /library).
    <div className="mw-app flex min-h-screen flex-col bg-background">
      <MarketingNav active="Insights" />

      <div className="flex-1">
        <div className="mx-auto max-w-6xl px-6 py-12 sm:py-16">
          <header className="flex flex-col gap-5 border-b border-border pb-6">
            <div className="flex flex-col gap-2">
              <span className="text-[13px] font-semibold uppercase tracking-[0.15em] text-primary">
                Marketworks
              </span>
              <h1 className="font-serif text-[2.5rem] font-medium leading-[1.08] tracking-[-0.02em] text-foreground sm:text-5xl">
                Insights
              </h1>
              <p className="max-w-2xl text-lg leading-[1.6] text-muted-foreground">
                A simple daily read on the Indian market — its trend, how calm or
                stressed it is, which sectors are leading, and the stocks on the
                move. Plus a screener that scores every stock the way our
                portfolios do. Educational, not investment advice.
              </p>
            </div>
            <InsightsTabs />
            <Suspense fallback={null}>
              <SnapshotPicker />
            </Suspense>
          </header>

          <div className="py-10">{children}</div>
        </div>
      </div>

      <MarketingFooter />
    </div>
  );
}
