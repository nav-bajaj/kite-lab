"use client";

import { useEffect } from "react";
import { AlertCircle, RefreshCw, Home } from "lucide-react";
import Link from "next/link";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Dashboard error:", error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="mx-auto max-w-md text-center">
        {/* Error icon */}
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10">
          <AlertCircle className="h-8 w-8 text-destructive" />
        </div>

        {/* Title */}
        <h2 className="mb-2 text-2xl font-bold tracking-tight">
          Something went wrong
        </h2>

        {/* Description */}
        <p className="mb-6 text-muted-foreground">
          An unexpected error occurred while loading this page. This has been
          logged and we&apos;ll look into it.
        </p>

        {/* Error details (dev only) */}
        {process.env.NODE_ENV === "development" && error.message && (
          <div className="mb-6 rounded-lg border bg-muted/50 p-4 text-left">
            <p className="mb-1 text-xs font-medium text-muted-foreground">
              Error Details
            </p>
            <code className="text-xs text-destructive">{error.message}</code>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-center gap-3">
          <button
            onClick={reset}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            Try Again
          </button>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium shadow-sm hover:bg-accent transition-colors"
          >
            <Home className="h-4 w-4" />
            Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
