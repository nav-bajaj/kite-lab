import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function RebalancePage() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Rebalance</CardTitle>
          <CardDescription>
            Weekly portfolio rebalancing and order management
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12 text-muted-foreground">
            <p>Rebalance functionality will be implemented in Phase 3</p>
            <p className="text-sm mt-2">
              Shows pending changes, generates order files, and tracks execution
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
