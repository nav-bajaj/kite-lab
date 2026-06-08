import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

// Recharts-free placeholders used as the `loading` fallback for the
// lazily-imported chart components. Kept in their own module (no recharts
// import) so pulling a fallback never drags the chart bundle back into the
// initial chunk. Dimensions mirror each chart's own skeleton to avoid
// layout shift (CLS) when the real chart swaps in.

export function EquityCurveFallback() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-4 w-48" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-[400px] w-full" />
      </CardContent>
    </Card>
  );
}

export function DrawdownChartFallback() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-24" />
        <Skeleton className="h-4 w-40" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-[250px] w-full" />
      </CardContent>
    </Card>
  );
}

export function AllocationChartFallback() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-4 w-40" />
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-center h-[300px]">
          <Skeleton className="h-[200px] w-[200px] rounded-full" />
        </div>
      </CardContent>
    </Card>
  );
}
