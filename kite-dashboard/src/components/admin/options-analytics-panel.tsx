"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, Loader2 } from "lucide-react";
import { useOptionsLiveAnalytics } from "@/lib/hooks";
import { cn } from "@/lib/utils";

// Live options analytics — parity forward, ATM IV, gamma profile and the
// heuristic regime read, computed server-side from the worker's 10-second
// chain snapshot. Measured quantities only (microstructure Stage 2);
// regime thresholds are uncalibrated until the day-type library matures.

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="space-y-0.5">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-sm font-medium tabular-nums">{value}</div>
    </div>
  );
}

const REGIME_STYLE: Record<string, string> = {
  "PIN-GRAVITY": "default",
  DIFFUSE: "secondary",
  MIXED: "outline",
};

export function OptionsAnalyticsPanel() {
  const { data, error, isLoading } = useOptionsLiveAnalytics();
  const a = data?.analytics;
  const ps = data?.paper_straddle;
  const stale = (data?.snapshot_age_seconds ?? 0) > 60;

  return (
    <Card>
      <CardHeader className="space-y-1">
        <CardTitle className="flex items-center gap-2">
          Options Analytics
          {a && (
            <Badge
              variant={(REGIME_STYLE[a.regime] ?? "outline") as "default" | "secondary" | "outline"}
              className="uppercase tracking-wide"
            >
              {a.regime}
            </Badge>
          )}
          {stale && (
            <Badge variant="secondary" className="uppercase tracking-wide">
              market closed
            </Badge>
          )}
        </CardTitle>
        <CardDescription>
          {data?.snapshot_at
            ? `From chain snapshot ${Math.round(data.snapshot_age_seconds ?? 0)}s old — measured only, regime heuristic`
            : "Live gamma/IV/regime from the worker's 10s chain snapshot"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {error ? (
          <div className="flex items-center gap-2 text-sm text-destructive">
            <AlertCircle className="h-4 w-4" />
            Failed to load analytics
          </div>
        ) : isLoading && !data ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : !data?.found || !a ? (
          <p className="text-sm text-muted-foreground">
            No chain snapshot yet — appears once the worker has captured.
          </p>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Stat label="Forward (parity)" value={a.forward.toFixed(1)} />
              <Stat label="ATM IV" value={a.atm_iv != null ? `${(a.atm_iv * 100).toFixed(2)}%` : "—"} />
              <Stat
                label="ATM straddle"
                value={a.atm_straddle != null ? `${a.atm_straddle.toFixed(1)} pts` : "—"}
              />
              <Stat label={`Expiry ${a.expiry}`} value={`ATM ${a.atm_strike.toFixed(0)}`} />
            </div>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Stat label="Total gamma / 1%" value={`₹${Math.round(a.total_gex_cr).toLocaleString("en-IN")}cr`} />
              <Stat label="Max-gamma strike" value={a.max_gamma_strike.toFixed(0)} />
              <Stat
                label="Concentration"
                value={a.concentration != null ? `${(a.concentration * 100).toFixed(0)}%` : "—"}
              />
              <Stat
                label="Paper straddle today"
                value={
                  ps ? (
                    <span className={cn((ps.live_pnl ?? ps.final_pnl) >= 0 ? "text-green-600 dark:text-green-500" : "text-destructive")}>
                      {(ps.live_pnl ?? ps.final_pnl) >= 0 ? "+" : ""}
                      {(ps.live_pnl ?? ps.final_pnl).toFixed(1)} pts
                      <span className="text-muted-foreground font-normal"> (MAE {ps.mae.toFixed(1)})</span>
                    </span>
                  ) : (
                    "—"
                  )
                }
              />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
