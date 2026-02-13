"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useRebalanceOrders } from "@/lib/hooks";
import { Download } from "lucide-react";
import { useUniverse } from "@/contexts/universe-context";

export function OrdersTable() {
  const { data, isLoading, error } = useRebalanceOrders();
  const { universeId } = useUniverse();

  const handleExport = () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    window.open(`${apiUrl}/api/rebalance/orders/export?universe=${universeId}`, "_blank");
  };

  if (isLoading) {
    return <OrdersTableSkeleton />;
  }

  if (error || !data) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">Failed to load orders</p>
        </CardContent>
      </Card>
    );
  }

  if (data.message) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Execution Orders</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{data.message}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Execution Orders</CardTitle>
            <CardDescription>
              {data.order_date
                ? `Order date: ${data.order_date}`
                : "Orders for execution"}
              {" - "}
              {data.sell_count} sells, {data.buy_count} buys
            </CardDescription>
          </div>
          {data.orders.length > 0 && (
            <Button variant="outline" size="sm" onClick={handleExport}>
              <Download className="h-4 w-4 mr-1" />
              Export CSV
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {data.orders.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            No orders available
          </p>
        ) : (
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Symbol</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead className="text-right">Shares</TableHead>
                  <TableHead className="text-right">Target Price</TableHead>
                  <TableHead className="text-right">Notional</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.orders.map((order, idx) => (
                  <TableRow key={`${order.symbol}-${idx}`}>
                    <TableCell className="font-medium">{order.symbol}</TableCell>
                    <TableCell>
                      <Badge
                        variant={order.action === "BUY" ? "default" : "destructive"}
                      >
                        {order.action}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {order.shares.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {order.target_price?.toFixed(2) || "-"}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {order.notional
                        ? order.notional.toLocaleString("en-IN", {
                            style: "currency",
                            currency: "INR",
                            maximumFractionDigits: 0,
                          })
                        : "-"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function OrdersTableSkeleton() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-4 w-48" />
          </div>
          <Skeleton className="h-9 w-28" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
