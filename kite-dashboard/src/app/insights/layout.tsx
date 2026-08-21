import { Suspense } from "react";
import { CompactSnapshotPicker } from "./_components/snapshot-picker";
import { UniverseSelector } from "./_components/universe-selector";
import {
  InsightsAppSidebar,
  InsightsTopbar,
  InsightsMobileNav,
} from "@/components/insights/shell";
import { DashboardMain } from "@/components/shared/dashboard-main";
import { DisclaimerFooter } from "@/components/shared/disclaimer-footer";
import { SidebarProvider } from "@/contexts/sidebar-context";

export const metadata = {
  title: "Insights — Marketworks",
  description:
    "A daily read on Indian markets — trend, stress, breadth and sector rotation with historical context, plus curated stock lists scored the way our portfolios are.",
};

export default function InsightsLayout({ children }: { children: React.ReactNode }) {
  return (
    // Full-screen app shell, same skeleton as the portfolios dashboard
    // (fixed collapsible sidebar + DashboardMain offset + top bar +
    // compliance footer). `.mw-app` so the finance up/down colours resolve.
    <SidebarProvider>
      <div className="mw-app flex min-h-screen flex-col bg-background">
        <Suspense fallback={null}>
          <InsightsAppSidebar />
        </Suspense>

        <DashboardMain>
          {/* The pickers only fit the header from `sm` up — at 390px the
              universe + snapshot + palette + avatar cluster needs 369px of a
              243px slot and pushes the page into horizontal scroll. Below
              `sm` they get their own full-width row instead. */}
          <InsightsTopbar
            pickerSlot={
              <div className="hidden items-center gap-1.5 sm:flex sm:gap-3">
                <Suspense fallback={null}>
                  <UniverseSelector />
                  <CompactSnapshotPicker />
                </Suspense>
              </div>
            }
          />

          <Suspense fallback={null}>
            <div className="flex flex-col gap-2 px-3 pt-2 lg:hidden">
              <InsightsMobileNav />
              <div className="flex items-center gap-1.5 sm:hidden">
                <UniverseSelector />
                <CompactSnapshotPicker />
              </div>
            </div>
          </Suspense>

          {/* div, not <main> — the pages render their own <main> landmark. */}
          <div className="flex-1 overflow-x-clip p-3 lg:p-5">{children}</div>

          <DisclaimerFooter />
        </DashboardMain>
      </div>
    </SidebarProvider>
  );
}
