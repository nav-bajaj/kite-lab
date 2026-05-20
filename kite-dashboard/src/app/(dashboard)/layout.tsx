import { Sidebar } from "@/components/shared/sidebar";
import { Navbar } from "@/components/shared/navbar";
import { DisclaimerFooter } from "@/components/shared/disclaimer-footer";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Desktop sidebar */}
      <Sidebar />

      {/* Main content area */}
      <div className="flex flex-1 flex-col lg:pl-64">
        {/* Top navbar */}
        <Navbar />

        {/* Page content */}
        <main className="flex-1 p-4 lg:p-6">{children}</main>

        {/* Persistent compliance footer */}
        <DisclaimerFooter />
      </div>
    </div>
  );
}
