import { Suspense } from "react";
import { CompactSnapshotPicker } from "./_components/snapshot-picker";
import { InsightsSidebar, InsightsMobileNav } from "@/components/insights/shell";
import { FloatingNav } from "@/components/marketing/floating-nav";
import { FooterPanel } from "@/components/marketing/footer-panel";
import { FlowGrid } from "@/components/marketing/flow-grid";

export const metadata = {
  title: "Insights — Marketworks",
  description:
    "A daily read on Indian markets — trend, stress, breadth and sector rotation with historical context, plus curated stock lists scored the way our portfolios are.",
};

export default function InsightsLayout({ children }: { children: React.ReactNode }) {
  return (
    // `.mw-app` (not `.mw-brand`) so the finance up/down colours resolve. The
    // floating nav stays SITE-level (Portfolios / Library / Insights) — the
    // insights sections live in the sidebar, mission-control style
    // (tasks/insights_dashboard_v2/DASHBOARD_DESIGN.md §1).
    <div className="mw-app relative flex min-h-screen flex-col overflow-hidden bg-surface-base">
      <FlowGrid />
      <FloatingNav />

      <div className="relative z-10 flex-1">
        <div className="mx-auto max-w-[1360px] px-4 pb-12 pt-24 sm:px-6 sm:pb-16 sm:pt-28">
          {/* The sidebar reads the ?date= param, so both nav variants need a
              suspense boundary around useSearchParams. */}
          <Suspense fallback={null}>
            <div className="mb-4 lg:hidden">
              <InsightsMobileNav />
            </div>
          </Suspense>
          <div className="flex gap-8">
            <Suspense fallback={<div className="hidden w-52 shrink-0 lg:block" />}>
              <InsightsSidebar />
            </Suspense>
            <div className="min-w-0 flex-1">
              <div className="mb-6 flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
                <span className="text-[13px] font-semibold uppercase tracking-[0.15em] text-primary">
                  Marketworks Insights
                </span>
                <Suspense fallback={null}>
                  <CompactSnapshotPicker />
                </Suspense>
              </div>
              {children}
            </div>
          </div>
        </div>
      </div>

      <div className="relative z-10 pb-6">
        <FooterPanel />
      </div>
    </div>
  );
}
