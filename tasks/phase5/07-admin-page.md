# Task 7: Admin Page Layout

**Status**: `pending`
**Blocked By**: None (can start in parallel with backend)
**Blocks**: None

## Objective

Create the admin page layout with grid sections for all admin components.

## Tasks

- [ ] Create admin page at `/admin`
- [ ] Set up responsive grid layout
- [ ] Add page header with system status indicator
- [ ] Import and position all admin components
- [ ] Add to sidebar navigation

## Implementation

### File: `kite-dashboard/src/app/(dashboard)/admin/page.tsx`

```tsx
"use client";

import {
  QuickActions,
  PortfolioGenerator,
  JobList,
  LogViewer,
  ScheduleTable,
  SystemStatus,
} from "@/components/admin";

export default function AdminPage() {
  return (
    <div className="space-y-6">
      {/* Page Header with System Status */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Admin Control Panel</h1>
          <p className="text-muted-foreground">
            Manage jobs, schedules, and system health
          </p>
        </div>
        <SystemStatus />
      </div>

      {/* Quick Actions */}
      <QuickActions />

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Left Column: Portfolio Generator */}
        <PortfolioGenerator />

        {/* Right Column: Job List */}
        <JobList />
      </div>

      {/* Log Viewer (Full Width) */}
      <LogViewer />

      {/* Schedule Table (Full Width) */}
      <ScheduleTable />
    </div>
  );
}
```

### Update Sidebar Navigation

Add to `kite-dashboard/src/components/layout/sidebar.tsx`:

```tsx
import { Settings } from "lucide-react";

const navItems = [
  { href: "/", label: "Portfolio", icon: Wallet },
  { href: "/performance", label: "Performance", icon: BarChart3 },
  { href: "/trades", label: "Trades", icon: ArrowLeftRight },
  { href: "/rebalance", label: "Rebalance", icon: RefreshCw },
  { href: "/admin", label: "Admin", icon: Settings },
];
```

### Create Component Index

### File: `kite-dashboard/src/components/admin/index.ts`

```typescript
export { QuickActions } from "./quick-actions";
export { PortfolioGenerator } from "./portfolio-generator";
export { JobList } from "./job-list";
export { LogViewer } from "./log-viewer";
export { ScheduleTable } from "./schedule-table";
export { SystemStatus } from "./system-status";
```

## Page Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Admin Control Panel                    [System Status: ●]   │
│ Manage jobs, schedules, and system health                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Quick Actions (full width)                            │   │
│  │ [🔄 Pipeline] [📊 Generate] [🔑 Login] [💾 Backup]    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌────────────────────────┐  ┌────────────────────────────┐ │
│  │ Portfolio Generator    │  │ Recent Jobs                │ │
│  │ (Card with form)       │  │ (Card with job list)       │ │
│  │                        │  │                            │ │
│  │ Universe: [▼ NSE500]   │  │ ┌────────────────────────┐ │ │
│  │ Lookback: [▼ 6 mo]     │  │ │ Daily Pipeline ● Done  │ │ │
│  │ ...                    │  │ │ 2 min ago             │ │ │
│  │ [Generate]             │  │ └────────────────────────┘ │ │
│  └────────────────────────┘  └────────────────────────────┘ │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Job Logs (full width)                        [Clear]  │   │
│  │ ┌────────────────────────────────────────────────────┐│   │
│  │ │ [07:00:01] Starting daily pipeline...              ││   │
│  │ │ [07:00:02] Fetching NSE 500 data...                ││   │
│  │ └────────────────────────────────────────────────────┘│   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Scheduled Jobs (full width)                           │   │
│  │ ┌────────┬───────────┬──────────┬─────────┬────────┐ │   │
│  │ │ Name   │ Schedule  │ Universe │ Next Run│ Action │ │   │
│  │ ├────────┼───────────┼──────────┼─────────┼────────┤ │   │
│  │ │ Daily  │ 07:00 IST │ All      │ Tomorrow│ [▶][✕] │ │   │
│  │ └────────┴───────────┴──────────┴─────────┴────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Mobile (<640px) | Single column, stacked |
| Tablet (640-1024px) | Single column, stacked |
| Desktop (>1024px) | Two column grid |

```tsx
// Grid classes for responsive layout
<div className="grid gap-6 lg:grid-cols-2">
  {/* Two columns on large screens, single column on smaller */}
</div>
```

## Component Dependencies

```
AdminPage
├── SystemStatus (header)
├── QuickActions (full width)
├── PortfolioGenerator (left column)
├── JobList (right column)
├── LogViewer (full width)
└── ScheduleTable (full width)
```

## State Management

```tsx
// Job selection state for log viewer
const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

// Pass to components
<JobList onSelectJob={setSelectedJobId} />
<LogViewer jobId={selectedJobId} />
```

## Verification

1. Navigate to `/admin` from sidebar
2. All components render without errors
3. Responsive layout works on mobile/tablet/desktop
4. System status indicator visible in header
5. Job selection updates log viewer

---

*Status Key: `pending` | `in_progress` | `completed`*
