"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useMonthlyReturns } from "@/lib/hooks";
import { cn } from "@/lib/utils";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function getColorForReturn(value: number): string {
  // Green gradient for positive, red gradient for negative
  if (value >= 10) return "bg-green-600";
  if (value >= 5) return "bg-green-500";
  if (value >= 2) return "bg-green-400";
  if (value >= 0) return "bg-green-200";
  if (value >= -2) return "bg-red-200";
  if (value >= -5) return "bg-red-400";
  if (value >= -10) return "bg-red-500";
  return "bg-red-600";
}

interface ReturnCellProps {
  value: number | null;
  isYtd?: boolean;
}

function ReturnCell({ value, isYtd }: ReturnCellProps) {
  if (value === null) {
    return (
      <div className="w-full h-8 rounded bg-muted/50 flex items-center justify-center">
        <span className="text-xs text-muted-foreground">-</span>
      </div>
    );
  }

  const bgColor = getColorForReturn(value);
  const textColor = Math.abs(value) > 5 ? "text-white" : "text-foreground";

  return (
    <div
      className={cn(
        "w-full h-8 rounded flex items-center justify-center",
        bgColor,
        textColor,
        isYtd && "font-semibold"
      )}
    >
      <span className="text-xs">
        {value >= 0 ? "+" : ""}
        {value.toFixed(1)}%
      </span>
    </div>
  );
}

export function MonthlyHeatmap() {
  const { data, isLoading, error } = useMonthlyReturns();

  if (isLoading) {
    return <MonthlyHeatmapSkeleton />;
  }

  if (error || !data?.data) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">Failed to load monthly returns</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Monthly Returns</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="text-left p-2 font-medium">Year</th>
                {MONTHS.map((month) => (
                  <th key={month} className="p-1 font-medium text-center text-xs">
                    {month}
                  </th>
                ))}
                <th className="p-1 font-medium text-center text-xs">YTD</th>
              </tr>
            </thead>
            <tbody>
              {data.data.map((row) => (
                <tr key={row.year}>
                  <td className="p-2 font-medium">{row.year}</td>
                  {row.months.map((value, idx) => (
                    <td key={idx} className="p-1">
                      <ReturnCell value={value} />
                    </td>
                  ))}
                  <td className="p-1">
                    <ReturnCell value={row.ytd} isYtd />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

function MonthlyHeatmapSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-32" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-[200px] w-full" />
      </CardContent>
    </Card>
  );
}
