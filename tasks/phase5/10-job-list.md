# Task 10: Job List Component

**Status**: `pending`
**Blocked By**: #2, #14 (Job Endpoints, API Client)
**Blocks**: None

## Objective

Create a list component showing recent jobs with status badges, timestamps, and click-to-view functionality.

## Tasks

- [ ] Create `job-list.tsx` in `components/admin/`
- [ ] Fetch jobs with SWR (auto-refresh)
- [ ] Implement status badges with colors
- [ ] Add relative timestamps
- [ ] Click to select job for log viewing
- [ ] Add cancel button for running jobs
- [ ] Add refresh button

## Implementation

### File: `kite-dashboard/src/components/admin/job-list.tsx`

```tsx
"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Loader2,
  RefreshCw,
  XCircle,
  Clock,
  CheckCircle2,
  AlertCircle,
  StopCircle,
  Timer,
} from "lucide-react";
import { useJobs, cancelJob } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";

interface JobListProps {
  onSelectJob?: (jobId: string) => void;
  selectedJobId?: string | null;
}

type JobStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

const statusConfig: Record<
  JobStatus,
  { label: string; icon: React.ElementType; variant: string; className: string }
> = {
  queued: {
    label: "Queued",
    icon: Clock,
    variant: "secondary",
    className: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  },
  running: {
    label: "Running",
    icon: Loader2,
    variant: "default",
    className: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  },
  completed: {
    label: "Completed",
    icon: CheckCircle2,
    variant: "success",
    className: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  },
  failed: {
    label: "Failed",
    icon: AlertCircle,
    variant: "destructive",
    className: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  },
  cancelled: {
    label: "Cancelled",
    icon: StopCircle,
    variant: "outline",
    className: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200",
  },
};

export function JobList({ onSelectJob, selectedJobId }: JobListProps) {
  const { data, isLoading, error, mutate } = useJobs({ limit: 20 });
  const [cancelling, setCancelling] = useState<string | null>(null);

  const handleCancel = async (jobId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setCancelling(jobId);

    try {
      await cancelJob(jobId);
      mutate(); // Refresh job list
    } catch (error) {
      console.error("Failed to cancel job:", error);
    } finally {
      setCancelling(null);
    }
  };

  const formatDuration = (seconds: number | null): string => {
    if (!seconds) return "";
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Recent Jobs</CardTitle>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => mutate()}
          disabled={isLoading}
        >
          <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
        </Button>
      </CardHeader>
      <CardContent>
        {error ? (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            Failed to load jobs
          </div>
        ) : isLoading && !data ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        ) : !data?.jobs?.length ? (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            No jobs found
          </div>
        ) : (
          <ScrollArea className="h-[300px]">
            <div className="space-y-2">
              {data.jobs.map((job) => {
                const config = statusConfig[job.status as JobStatus];
                const StatusIcon = config?.icon || Clock;
                const isSelected = selectedJobId === job.id;
                const isRunning = job.status === "running";
                const isQueued = job.status === "queued";

                return (
                  <div
                    key={job.id}
                    className={cn(
                      "flex items-center justify-between rounded-lg border p-3 cursor-pointer transition-colors",
                      isSelected
                        ? "border-primary bg-primary/5"
                        : "hover:bg-muted/50"
                    )}
                    onClick={() => onSelectJob?.(job.id)}
                  >
                    <div className="flex items-center gap-3">
                      <StatusIcon
                        className={cn(
                          "h-4 w-4",
                          isRunning && "animate-spin text-blue-500",
                          job.status === "completed" && "text-green-500",
                          job.status === "failed" && "text-red-500"
                        )}
                      />
                      <div>
                        <div className="font-medium">
                          {job.label || job.command}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <span>
                            {formatDistanceToNow(new Date(job.created_at), {
                              addSuffix: true,
                            })}
                          </span>
                          {job.duration_seconds && (
                            <>
                              <span>·</span>
                              <span className="flex items-center gap-1">
                                <Timer className="h-3 w-3" />
                                {formatDuration(job.duration_seconds)}
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <Badge className={config?.className}>
                        {config?.label || job.status}
                      </Badge>

                      {(isRunning || isQueued) && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={(e) => handleCancel(job.id, e)}
                          disabled={cancelling === job.id}
                        >
                          {cancelling === job.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <XCircle className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                          )}
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}
```

## Status Badges

| Status | Icon | Color | Description |
|--------|------|-------|-------------|
| Queued | Clock | Yellow | Waiting to run |
| Running | Loader2 (spinning) | Blue | Currently executing |
| Completed | CheckCircle2 | Green | Successfully finished |
| Failed | AlertCircle | Red | Error occurred |
| Cancelled | StopCircle | Gray | Manually stopped |

## Job Item Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ● Daily Pipeline                            [Completed]     │
│   2 min ago · ⏱ 5m 32s                                     │
├─────────────────────────────────────────────────────────────┤
│ ◐ Generate NSE500                           [Running] [✕]   │
│   5 min ago                                                 │
├─────────────────────────────────────────────────────────────┤
│ ✗ Backup Data                               [Failed]        │
│   1 hour ago · ⏱ 0m 12s                                    │
└─────────────────────────────────────────────────────────────┘
```

## Props

| Prop | Type | Description |
|------|------|-------------|
| onSelectJob | `(jobId: string) => void` | Callback when job is clicked |
| selectedJobId | `string \| null` | Currently selected job ID |

## Auto-Refresh

Using SWR with automatic refresh:

```tsx
const { data, isLoading, error, mutate } = useJobs({
  limit: 20,
  refreshInterval: 5000, // Refresh every 5 seconds
});
```

## Click Interaction

- Click job row to select it
- Selected job highlighted with border
- onSelectJob callback triggers log viewer update

## Cancel Button

- Shows only for queued/running jobs
- Click stops propagation (doesn't select job)
- Loading state while cancelling
- Refreshes list after cancel

## Verification

1. Jobs list loads on page load
2. Status badges show correct colors
3. Relative timestamps update
4. Duration shows for completed jobs
5. Click selects job (highlighted)
6. Cancel button works for running jobs
7. Refresh button reloads list
8. Auto-refresh updates running jobs

---

*Status Key: `pending` | `in_progress` | `completed`*
