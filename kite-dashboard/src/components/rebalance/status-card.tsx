"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useRebalanceStatus } from "@/lib/hooks";
import { Calendar, Clock, CheckCircle, AlertCircle } from "lucide-react";

export function StatusCard() {
  const { data, isLoading, error } = useRebalanceStatus();

  if (isLoading) {
    return <StatusCardSkeleton />;
  }

  if (error || !data) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">Failed to load rebalance status</p>
        </CardContent>
      </Card>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "executed":
        return "bg-green-100 text-green-800";
      case "ready":
        return "bg-blue-100 text-blue-800";
      case "preview":
        return "bg-yellow-100 text-yellow-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getPhaseIcon = (phase: string) => {
    switch (phase) {
      case "ready":
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case "preview":
        return <AlertCircle className="h-5 w-5 text-yellow-600" />;
      default:
        return <Clock className="h-5 w-5 text-gray-400" />;
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Rebalance Status</CardTitle>
            <CardDescription>
              {data.today} ({data.weekday})
            </CardDescription>
          </div>
          {getPhaseIcon(data.current_phase)}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Current Phase</span>
            <Badge className={getStatusColor(data.current_phase)}>
              {data.current_phase.toUpperCase()}
            </Badge>
          </div>

          {data.is_rebalance_day && (
            <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-950">
              <p className="text-sm font-medium text-blue-800 dark:text-blue-200">
                {data.weekday === "Thu"
                  ? "Today is preview day - review upcoming changes"
                  : "Today is order day - execute rebalance orders"}
              </p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4 pt-2">
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Signal Date</p>
                <p className="text-sm font-medium">{data.signal_date || "N/A"}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Order Date</p>
                <p className="text-sm font-medium">{data.order_date || "N/A"}</p>
              </div>
            </div>
          </div>

          <div className="flex gap-2 pt-2">
            {data.preview_available && (
              <Badge variant="outline" className="text-green-600 border-green-600">
                Preview Available
              </Badge>
            )}
            {data.orders_available && (
              <Badge variant="outline" className="text-blue-600 border-blue-600">
                Orders Available
              </Badge>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function StatusCardSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-4 w-24" />
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      </CardContent>
    </Card>
  );
}
