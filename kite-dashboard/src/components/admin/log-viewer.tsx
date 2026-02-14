"use client";

import { useEffect, useRef, useCallback, useState, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Copy, Trash2, Download, Loader2, Terminal } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useJobLogs, useJob } from "@/lib/hooks";
import { getJobLogsStreamUrl } from "@/lib/api-client";

interface LogViewerProps {
  jobId: string | null;
  autoScroll?: boolean;
}

// Inner component that handles streaming - keyed by jobId to reset state
function LogViewerInner({
  jobId,
  autoScroll,
  baseLogs,
  isLoading,
  jobStatus,
}: {
  jobId: string;
  autoScroll: boolean;
  baseLogs: string;
  isLoading: boolean;
  jobStatus: string | undefined;
}) {
  const [streamingLogs, setStreamingLogs] = useState<string>("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [cleared, setCleared] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const { toast } = useToast();

  // Determine which logs to display
  const displayLogs = useMemo(() => {
    if (cleared) return "";
    return streamingLogs || baseLogs;
  }, [cleared, streamingLogs, baseLogs]);

  // Stream logs for running jobs
  useEffect(() => {
    // Close existing stream
    const closeStream = () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };

    if (jobStatus !== "running") {
      closeStream();
      return;
    }

    // Start SSE stream
    const url = getJobLogsStreamUrl(jobId);
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    // Initialize state when connection opens
    eventSource.onopen = () => {
      setIsStreaming(true);
      setStreamingLogs(baseLogs);
    };

    eventSource.onmessage = (event) => {
      setStreamingLogs((prev) => prev + event.data + "\n");
    };

    const handleDone = () => {
      closeStream();
      setIsStreaming(false);
    };

    eventSource.addEventListener("done", handleDone);

    eventSource.onerror = () => {
      closeStream();
      setIsStreaming(false);
    };

    return () => {
      closeStream();
    };
  }, [jobId, jobStatus, baseLogs]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoScroll && scrollRef.current && displayLogs) {
      const scrollContainer = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
      }
    }
  }, [displayLogs, autoScroll]);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(displayLogs);
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
  }, [displayLogs, toast]);

  const handleClear = useCallback(() => {
    setCleared(true);
    setStreamingLogs("");
  }, []);

  const handleDownload = useCallback(() => {
    const blob = new Blob([displayLogs], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `job-${jobId}.log`;
    a.click();
    URL.revokeObjectURL(url);
  }, [displayLogs, jobId]);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <CardTitle>Job Logs</CardTitle>
          {isStreaming && (
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
            disabled={!displayLogs}
            title="Copy to clipboard"
          >
            <Copy className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleDownload}
            disabled={!displayLogs}
            title="Download logs"
          >
            <Download className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleClear}
            disabled={!displayLogs}
            title="Clear logs"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        ) : (
          <ScrollArea
            ref={scrollRef}
            className="h-[300px] rounded-md border bg-muted/30"
          >
            <pre className="p-4 font-mono text-sm leading-relaxed whitespace-pre-wrap">
              {displayLogs || "No logs available"}
            </pre>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}

export function LogViewer({ jobId, autoScroll = true }: LogViewerProps) {
  // Fetch initial logs and job status
  const { data: logsData, isLoading } = useJobLogs(jobId);
  const { data: job } = useJob(jobId);

  if (!jobId) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Job Logs</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <Terminal className="mb-2 h-8 w-8" />
            <p>Select a job to view logs</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Key by jobId to reset inner state when job changes
  return (
    <LogViewerInner
      key={jobId}
      jobId={jobId}
      autoScroll={autoScroll}
      baseLogs={logsData?.logs ?? ""}
      isLoading={isLoading}
      jobStatus={job?.status}
    />
  );
}
