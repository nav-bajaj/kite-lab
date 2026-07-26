import { Sidebar } from "@/components/shared/sidebar";
import { Navbar } from "@/components/shared/navbar";
import { BottomNav } from "@/components/shared/bottom-nav";
import { DashboardMain } from "@/components/shared/dashboard-main";
import { DisclaimerFooter } from "@/components/shared/disclaimer-footer";
import { SidebarProvider } from "@/contexts/sidebar-context";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SidebarProvider>
      <div className="mw-app flex min-h-screen flex-col bg-background">
        {/* Desktop sidebar */}
        <Sidebar />

        {/* Main content area — left offset tracks the sidebar width */}
        <DashboardMain>
          {/* Top navbar */}
          <Navbar />

          {/* Page content */}
          {/* Extra bottom padding below md clears the floating BottomNav */}
          <main className="flex-1 overflow-x-clip p-4 pb-28 md:pb-4 lg:p-6">{children}</main>

          {/* Persistent compliance footer */}
          <div className="pb-24 md:pb-0">
            <DisclaimerFooter />
          </div>
        </DashboardMain>

        {/* Mobile bottom navigation (UX study D3) */}
        <BottomNav />
      </div>
    </SidebarProvider>
  );
}
