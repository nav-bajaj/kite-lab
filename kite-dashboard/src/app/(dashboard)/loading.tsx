import { Skeleton } from "@/components/ui/skeleton";

// Route-level fallback shown during navigation between dashboard pages.
// The sidebar/navbar in the (dashboard) layout stay mounted; this only
// fills the page content area, so it's a generic header + cards + body
// skeleton sized to roughly match every page and avoid layout shift.
export default function DashboardLoading() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-72" />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28 w-full" />
        ))}
      </div>

      <Skeleton className="h-[360px] w-full" />
    </div>
  );
}
