"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { AlertCircle, Download, Loader2, RefreshCw } from "lucide-react";
import { useWaitlist } from "@/lib/hooks";
import { fetchWaitlistCsv } from "@/lib/api-client";
import type { WaitlistStatus } from "@/lib/api-client";

// Launch-waitlist readout (tasks/email_channel Phase 1). Read-only: the
// list is written by the public coming-soon form and mutated only by the
// consent endpoints, never from here.

// Switch rather than a keyed object: the key comes from an API payload, so
// a dynamic index trips eslint-plugin-security (R-007) and would also
// render `undefined` if the backend ever grew a status the UI predates.
function statusLabel(status: WaitlistStatus): string {
  switch (status) {
    case "pending":
      return "Pending";
    case "confirmed":
      return "Confirmed";
    case "unsubscribed":
      return "Unsubscribed";
    case "bounced":
      return "Bounced";
    case "complained":
      return "Complained";
    default:
      return String(status);
  }
}

function statusDotClass(status: WaitlistStatus): string {
  switch (status) {
    case "confirmed":
      return "bg-green-500";
    case "pending":
      return "bg-amber-500";
    case "unsubscribed":
      return "bg-muted-foreground";
    default:
      return "bg-red-500";
  }
}

function fmt(ts: string | null): string {
  if (!ts) return "—";
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleString();
}

export function WaitlistPanel() {
  const { data, error, isLoading, mutate } = useWaitlist();
  const [downloading, setDownloading] = useState(false);

  // The export needs the bearer token, so fetch it and hand the browser a
  // blob rather than linking straight at the endpoint.
  async function handleExport() {
    setDownloading(true);
    try {
      const blob = await fetchWaitlistCsv();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `waitlist-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      // Surfaced by the row below rather than a toast — this panel is ops
      // furniture, not a flow the founder is guided through.
    } finally {
      setDownloading(false);
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle>Launch waitlist</CardTitle>
          <CardDescription>
            Signups from the under-development page. Only confirmed
            addresses are mailable.
          </CardDescription>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => mutate()}
            disabled={isLoading}
          >
            <RefreshCw
              className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`}
            />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleExport}
            disabled={downloading || !data?.count}
          >
            {downloading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            <span className="ml-2">CSV</span>
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        {error && (
          <div className="flex items-center gap-2 text-sm text-destructive">
            <AlertCircle className="h-4 w-4" />
            Could not load the waitlist.
          </div>
        )}

        {!error && isLoading && !data && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading…
          </div>
        )}

        {data && (
          <>
            <div className="mb-5 flex flex-wrap items-baseline gap-x-8 gap-y-2">
              <div>
                <div className="font-mono text-3xl tabular-nums">
                  {data.count}
                </div>
                <div className="text-xs text-muted-foreground">
                  total signups
                </div>
              </div>
              <div>
                <div className="font-mono text-3xl tabular-nums text-green-600">
                  {data.mailable}
                </div>
                <div className="text-xs text-muted-foreground">mailable</div>
              </div>
              <div className="flex flex-wrap gap-2">
                {(
                  Object.entries(data.by_status) as [WaitlistStatus, number][]
                )
                  .filter(([, n]) => n > 0)
                  .map(([s, n]) => (
                    <Badge key={s} variant="outline" className="gap-1.5">
                      <span
                        className={`h-2 w-2 rounded-full ${statusDotClass(s)}`}
                      />
                      {statusLabel(s)} {n}
                    </Badge>
                  ))}
              </div>
            </div>

            {data.count === 0 ? (
              <p className="text-sm text-muted-foreground">
                No signups yet.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Signed up</TableHead>
                    <TableHead>Confirmed</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.signups.map((s) => (
                    <TableRow key={s.email}>
                      <TableCell className="font-mono text-xs">
                        {s.email}
                      </TableCell>
                      <TableCell>
                        <span className="inline-flex items-center gap-1.5 text-xs">
                          <span
                            className={`h-2 w-2 rounded-full ${statusDotClass(s.status)}`}
                          />
                          {statusLabel(s.status)}
                        </span>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {fmt(s.created_at)}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {fmt(s.confirmed_at)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
