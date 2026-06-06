import { Sidebar } from "@/components/shared/sidebar";
import { Navbar } from "@/components/shared/navbar";
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
          <main className="flex-1 p-4 lg:p-6">{children}</main>

          {/* Persistent compliance footer */}
          <DisclaimerFooter />
        </DashboardMain>
      </div>
    </SidebarProvider>
  );
}
