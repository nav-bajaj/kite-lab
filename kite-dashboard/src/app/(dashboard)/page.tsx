import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Wallet, BarChart3 } from "lucide-react";

export default function DashboardPage() {
  // Placeholder data - will be replaced with API data in Task #11
  const stats = [
    {
      title: "Portfolio Value",
      value: "₹78,20,005",
      change: "+682.0%",
      trend: "up" as const,
      icon: Wallet,
    },
    {
      title: "Today's P&L",
      value: "₹12,450",
      change: "+0.16%",
      trend: "up" as const,
      icon: TrendingUp,
    },
    {
      title: "CAGR",
      value: "59.4%",
      change: "vs 15% Nifty",
      trend: "up" as const,
      icon: BarChart3,
    },
    {
      title: "Max Drawdown",
      value: "-30.0%",
      change: "Historical",
      trend: "down" as const,
      icon: TrendingDown,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
              <stat.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p
                className={`text-xs ${
                  stat.trend === "up" ? "text-green-600" : "text-red-600"
                }`}
              >
                {stat.change}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Holdings Table Placeholder */}
      <Card>
        <CardHeader>
          <CardTitle>Current Holdings</CardTitle>
          <CardDescription>
            Top 24 momentum stocks in NSE 500 portfolio
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12 text-muted-foreground">
            <p>Holdings data will be loaded from API</p>
            <p className="text-sm mt-2">Complete Task #11 to enable API integration</p>
          </div>
        </CardContent>
      </Card>

      {/* Equity Curve Placeholder */}
      <Card>
        <CardHeader>
          <CardTitle>Portfolio Performance</CardTitle>
          <CardDescription>
            Equity curve vs Nifty 100 benchmark (2020-2026)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12 text-muted-foreground">
            <p>Performance chart will be displayed here</p>
            <p className="text-sm mt-2">Recharts integration coming in Phase 2</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
