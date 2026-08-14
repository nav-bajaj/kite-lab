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
          <InsightsTopbar
            pickerSlot={
              <Suspense fallback={null}>
                <UniverseSelector />
                <CompactSnapshotPicker />
              </Suspense>
            }
          />

          <Suspense fallback={null}>
            <div className="px-4 pt-3 lg:hidden">
              <InsightsMobileNav />
            </div>
          </Suspense>

          {/* div, not <main> — the pages render their own <main> landmark. */}
          <div className="flex-1 overflow-x-clip p-4 lg:p-6">{children}</div>

          <DisclaimerFooter />
        </DashboardMain>
      </div>
    </SidebarProvider>
  );
}
