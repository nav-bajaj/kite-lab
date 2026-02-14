"use client";

import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Activity,
  Key,
  RefreshCw,
  Cloud,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { useSystemStatus } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";

interface StatusIndicatorProps {
  status: boolean;
  label: string;
  detail?: string;
}

function StatusIndicator({ status, label, detail }: StatusIndicatorProps) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        {status ? (
          <CheckCircle2 className="h-4 w-4 text-green-500" />
        ) : (
          <XCircle className="h-4 w-4 text-red-500" />
        )}
        <span className="text-sm">{label}</span>
      </div>
      {detail && (
        <span className="text-xs text-muted-foreground">{detail}</span>
      )}
    </div>
  );
}

export function SystemStatus() {
  const { data, isLoading, error, mutate } = useSystemStatus();

  // Determine overall status
  const isHealthy =
    data?.api_health &&
    data?.database?.connected &&
    data?.token?.valid;

  const getStatusColor = () => {
    if (isLoading) return "bg-gray-400";
    if (error) return "bg-red-500";
    if (!isHealthy) return "bg-yellow-500";
    return "bg-green-500";
  };

  const getStatusText = () => {
    if (isLoading) return "Checking...";
    if (error) return "Error";
    if (!isHealthy) return "Warning";
    return "Healthy";
  };

  const formatExpiry = (expiresAt: string | null) => {
    if (!expiresAt) return "Unknown";
    const date = new Date(expiresAt);
    return formatDistanceToNow(date, { addSuffix: true });
  };

  const formatLastSync = (lastSync: string | null) => {
    if (!lastSync) return "Never";
    return formatDistanceToNow(new Date(lastSync), { addSuffix: true });
  };

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" className="gap-2">
          <span
            className={cn(
              "h-2 w-2 rounded-full",
              getStatusColor(),
              isLoading && "animate-pulse"
            )}
          />
          <span className="hidden sm:inline">{getStatusText()}</span>
          <Activity className="h-4 w-4" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80" align="end">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="font-medium">System Status</h4>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => mutate()}
              disabled={isLoading}
            >
              <RefreshCw className={cn("h-3 w-3", isLoading && "animate-spin")} />
            </Button>
          </div>

          {error ? (
            <div className="flex items-center gap-2 text-sm text-destructive">
              <AlertCircle className="h-4 w-4" />
              Failed to load status
            </div>
          ) : isLoading && !data ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : (
            <>
              <StatusIndicator
                status={data?.api_health || false}
                label="API Server"
                detail={data?.version}
              />

              <StatusIndicator
                status={data?.database?.connected || false}
                label="Database"
                detail={
                  data?.database?.connected
                    ? `${data?.database?.latency_ms}ms`
                    : data?.database?.message
                }
              />

              <Separator />

              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Key className="h-4 w-4" />
                  <span className="text-sm font-medium">Kite Token</span>
                </div>
                <div className="ml-6 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Status</span>
                    <Badge
                      variant={data?.token?.valid ? "default" : "destructive"}
                    >
                      {data?.token?.valid ? "Valid" : "Expired"}
                    </Badge>
                  </div>
                  {data?.token?.expires_at && (
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>Expires</span>
                      <span>{formatExpiry(data?.token?.expires_at)}</span>
                    </div>
                  )}
                  {!data?.token?.valid && (
                    <p className="text-xs text-muted-foreground">
                      {data?.token?.message}
                    </p>
                  )}
                </div>
              </div>

              <Separator />

              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Cloud className="h-4 w-4" />
                  <span className="text-sm font-medium">Data Sync</span>
                </div>
                <div className="ml-6 space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span>Last sync</span>
                    <span className="text-muted-foreground">
                      {formatLastSync(data?.sync?.last_sync || null)}
                    </span>
                  </div>
                  {data?.sync?.last_data_date && (
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>Data date</span>
                      <span>{data?.sync?.last_data_date}</span>
                    </div>
                  )}
                  <p className="text-xs text-muted-foreground">
                    {data?.sync?.message}
                  </p>
                </div>
              </div>

              <Separator />

              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Environment</span>
                <Badge variant="outline">{data?.environment}</Badge>
              </div>
            </>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}
