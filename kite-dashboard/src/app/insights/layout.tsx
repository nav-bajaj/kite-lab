import { Suspense } from "react";
import { SnapshotPicker } from "./_components/snapshot-picker";
import { InsightsTabs } from "@/components/insights/tabs";
import { FloatingNav } from "@/components/marketing/floating-nav";
import { FooterPanel } from "@/components/marketing/footer-panel";
import { FlowGrid } from "@/components/marketing/flow-grid";

export const metadata = {
  title: "Insights — Marketworks",
  description:
    "A simple daily read on Indian markets — trend, stress, sector leaders, and a screener that scores every stock the way our portfolios do.",
};

export default function InsightsLayout({ children }: { children: React.ReactNode }) {
  return (
    // `.mw-app` (not `.mw-brand`) so the finance up/down colours resolve, while
    // the floating glass nav + quant-grid base + footer panel give Insights
    // the same layered site chrome as the redesigned marketing surfaces.
    <div className="mw-app relative flex min-h-screen flex-col overflow-hidden bg-surface-base">
      <FlowGrid />
      <FloatingNav />

      <div className="relative z-10 flex-1">
        <div className="mx-auto max-w-6xl px-6 pb-12 pt-28 sm:pb-16 sm:pt-32">
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

      <div className="relative z-10 pb-6">
        <FooterPanel />
      </div>
    </div>
  );
}
