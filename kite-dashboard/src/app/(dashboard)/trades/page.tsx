import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function TradesPage() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Trade History</CardTitle>
          <CardDescription>
            All executed trades with P&L analysis
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12 text-muted-foreground">
            <p>Trade history will be implemented in Phase 3</p>
            <p className="text-sm mt-2">
              Includes filtering, sorting, and export functionality
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
