# Task 11: Log Viewer Component

**Status**: `pending`
**Blocked By**: #2, #14 (Job Endpoints, API Client)
**Blocks**: None

## Objective

Create a log viewer with monospace text area, auto-scroll, SSE streaming, copy, and clear buttons.

## Tasks

- [ ] Create `log-viewer.tsx` in `components/admin/`
- [ ] Implement monospace text display
- [ ] Add auto-scroll to bottom
- [ ] Implement SSE streaming for live updates
- [ ] Add copy to clipboard button
- [ ] Add clear logs button
- [ ] Show empty state when no job selected

## Implementation

### File: `kite-dashboard/src/components/admin/log-viewer.tsx`

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Copy, Trash2, Download, Loader2, Terminal } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
import { useJobLogs, getJobLogsStreamUrl } from "@/lib/api-client";
import { cn } from "@/lib/utils";

interface LogViewerProps {
  jobId: string | null;
  autoScroll?: boolean;
}

export function LogViewer({ jobId, autoScroll = true }: LogViewerProps) {
  const [logs, setLogs] = useState<string>("");
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const { toast } = useToast();

  // Fetch initial logs
  const { data: logsData, isLoading } = useJobLogs(jobId);

  // Set initial logs when data loads
  useEffect(() => {
    if (logsData?.logs) {
      setLogs(logsData.logs);
    }
  }, [logsData]);

  // Stream logs for running jobs
  useEffect(() => {
    if (!jobId || logsData?.status !== "running") {
      // Close any existing stream
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
        setStreaming(false);
      }
      return;
    }

    // Start SSE stream
    const url = getJobLogsStreamUrl(jobId);
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;
    setStreaming(true);

    eventSource.onmessage = (event) => {
      setLogs((prev) => prev + event.data + "\n");
    };

    eventSource.addEventListener("done", (event) => {
      eventSource.close();
      eventSourceRef.current = null;
      setStreaming(false);
    });

    eventSource.onerror = () => {
      eventSource.close();
      eventSourceRef.current = null;
      setStreaming(false);
    };

    return () => {
      eventSource.close();
      eventSourceRef.current = null;
      setStreaming(false);
    };
  }, [jobId, logsData?.status]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(logs);
      toast({
        title: "Copied",
        description: "Logs copied to clipboard",
      });
    } catch {
      toast({
        title: "Error",
        description: "Failed to copy logs",
        variant: "destructive",
      });
    }
  };

  const handleClear = () => {
    setLogs("");
  };

  const handleDownload = () => {
    const blob = new Blob([logs], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `job-${jobId || "logs"}.log`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <CardTitle>Job Logs</CardTitle>
          {streaming && (
            <Badge variant="secondary" className="animate-pulse">
              <Loader2 className="mr-1 h-3 w-3 animate-spin" />
              Streaming
            </Badge>
          )}
        </div>
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={handleCopy}
            disabled={!logs}
            title="Copy to clipboard"
          >
            <Copy className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleDownload}
            disabled={!logs}
            title="Download logs"
          >
            <Download className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleClear}
            disabled={!logs}
            title="Clear logs"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {!jobId ? (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <Terminal className="mb-2 h-8 w-8" />
            <p>Select a job to view logs</p>
          </div>
        ) : isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        ) : (
          <ScrollArea
            ref={scrollRef}
            className="h-[300px] rounded-md border bg-muted/30"
          >
            <pre className="p-4 font-mono text-sm leading-relaxed">
              {logs || "No logs available"}
            </pre>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}
```

## Features

### SSE Streaming

Real-time log updates using Server-Sent Events:

```tsx
const eventSource = new EventSource(url);

eventSource.onmessage = (event) => {
  setLogs((prev) => prev + event.data + "\n");
};

eventSource.addEventListener("done", () => {
  eventSource.close();
});
```

### Auto-Scroll

Automatically scrolls to bottom when new logs arrive:

```tsx
useEffect(() => {
  if (autoScroll && scrollRef.current) {
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }
}, [logs, autoScroll]);
```

### Actions

| Button | Icon | Description |
|--------|------|-------------|
| Copy | Copy | Copy logs to clipboard |
| Download | Download | Save as .log file |
| Clear | Trash2 | Clear log display |

## Log Display

```
┌─────────────────────────────────────────────────────────────┐
│ Job Logs                    [Streaming]  [📋] [⬇] [🗑]     │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ [2026-02-14T07:00:01] Starting job: daily_pipeline      │ │
│ │ [2026-02-14T07:00:01] Command: python scripts/run...    │ │
│ │ ────────────────────────────────────────────────────    │ │
│ │ Logging in to Kite API...                               │ │
│ │ Login successful                                        │ │
│ │ Fetching NSE 500 data...                                │ │
│ │ [100/499] Fetched RELIANCE                              │ │
│ │ [200/499] Fetched TCS                                   │ │
│ │ ...                                                     │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| jobId | `string \| null` | required | Job ID to show logs for |
| autoScroll | `boolean` | `true` | Auto-scroll to bottom |

## States

### Empty State (no job selected)
```
┌─────────────────────┐
│       [icon]        │
│ Select a job to     │
│ view logs           │
└─────────────────────┘
```

### Loading State
```
┌─────────────────────┐
│      [spinner]      │
└─────────────────────┘
```

### Streaming State
Shows "Streaming" badge with animation while receiving logs.

## Styling

```css
/* Monospace font for logs */
pre {
  font-family: ui-monospace, monospace;
  font-size: 0.875rem;
  line-height: 1.625;
}

/* Muted background for log area */
.log-area {
  background: hsl(var(--muted) / 0.3);
}
```

## Verification

1. Select job from job list
2. Logs load and display
3. Running jobs stream live updates
4. Auto-scroll follows new logs
5. Copy button copies to clipboard
6. Download saves .log file
7. Clear button clears display
8. Streaming badge shows for running jobs
9. Empty state when no job selected

---

*Status Key: `pending` | `in_progress` | `completed`*
