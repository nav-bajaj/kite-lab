import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function PerformancePage() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Performance Analytics</CardTitle>
          <CardDescription>
            Detailed performance metrics and charts
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12 text-muted-foreground">
            <p>Performance analytics will be implemented in Phase 2</p>
            <p className="text-sm mt-2">
              Includes equity curves, drawdown analysis, and monthly returns
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
