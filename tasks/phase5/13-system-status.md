# Task 13: System Status Component

**Status**: `pending`
**Blocked By**: #4, #14 (System Endpoints, API Client)
**Blocks**: None

## Objective

Create a status indicator component showing API health, database connection, token status, and last sync.

## Tasks

- [ ] Create `system-status.tsx` in `components/admin/`
- [ ] Implement status indicators (green/red dots)
- [ ] Show token expiry time
- [ ] Show last sync timestamp
- [ ] Add refresh button
- [ ] Implement popover with full details

## Implementation

### File: `kite-dashboard/src/components/admin/system-status.tsx`

```tsx
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
  Database,
  Key,
  RefreshCw,
  Cloud,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { useSystemStatus } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { formatDistanceToNow, format } from "date-fns";

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
              {/* API Health */}
              <StatusIndicator
                status={data?.api_health || false}
                label="API Server"
                detail={data?.version}
              />

              {/* Database */}
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

              {/* Token Status */}
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

              {/* Sync Status */}
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

              {/* Environment */}
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
```

## Status Button

The main button shows overall status:

```
┌────────────────────┐
│ ● Healthy [icon]   │
└────────────────────┘
```

### Status Colors

| Status | Color | Condition |
|--------|-------|-----------|
| Healthy | Green | All systems OK |
| Warning | Yellow | Token expired or sync old |
| Error | Red | API or DB down |
| Checking | Gray (pulsing) | Loading |

## Popover Content

```
┌──────────────────────────────────┐
│ System Status              [↻]   │
├──────────────────────────────────┤
│ ✓ API Server            v1.0.1  │
│ ✓ Database              2.34ms  │
├──────────────────────────────────┤
│ 🔑 Kite Token                    │
│    Status            [Valid]     │
│    Expires           in 12 hours │
├──────────────────────────────────┤
│ ☁ Data Sync                      │
│    Last sync         2 hours ago │
│    Data date         2026-02-13  │
│    Data is 1 day old             │
├──────────────────────────────────┤
│    Environment       [production]│
└──────────────────────────────────┘
```

## Indicators

### API Health
- Green checkmark: API responding
- Red X: API unreachable

### Database
- Green checkmark: Connected
- Shows latency in ms
- Red X with error message if failed

### Token Status
- Badge: Valid (default) / Expired (destructive)
- Expiry time in relative format
- Message if expired

### Sync Status
- Last sync time (relative)
- Latest data date
- Freshness message

## Verification

1. Status button shows in header
2. Click opens popover
3. All status indicators display
4. Token expiry shows relative time
5. Sync status shows data freshness
6. Refresh button reloads status
7. Warning state when token expired
8. Error state when API down

---

*Status Key: `pending` | `in_progress` | `completed`*
