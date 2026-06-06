"use client";

import { useSidebar } from "@/contexts/sidebar-context";
import { cn } from "@/lib/utils";

/**
 * Main content column for the dashboard. Its left offset follows the sidebar
 * width so collapsing the rail reclaims the space instead of leaving a gap.
 */
export function DashboardMain({ children }: { children: React.ReactNode }) {
  const { collapsed } = useSidebar();

  return (
    <div
      className={cn(
        "flex flex-1 flex-col transition-[padding] duration-300",
        collapsed ? "lg:pl-16" : "lg:pl-48",
      )}
    >
      {children}
    </div>
  );
}
