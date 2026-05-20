import Link from "next/link";

/**
 * Persistent footer rendered on every authenticated dashboard page.
 *
 * Required for compliance: model portfolios are research output, not
 * regulated investment advice. Keep this visible on every page so
 * clients aren't ever a click away from the disclaimer.
 */
export function DisclaimerFooter() {
  return (
    <footer className="border-t border-border bg-background/50 px-4 py-3 text-xs text-muted-foreground lg:px-6">
      <div className="flex flex-col items-center justify-between gap-2 sm:flex-row">
        <p>
          Model portfolios — research output, not investment advice. Past
          performance is not indicative of future returns.
        </p>
        <nav className="flex items-center gap-4">
          <Link href="/disclaimer" className="hover:text-foreground">
            Disclaimer
          </Link>
          <Link href="/terms" className="hover:text-foreground">
            Terms
          </Link>
          <Link href="/privacy" className="hover:text-foreground">
            Privacy
          </Link>
        </nav>
      </div>
    </footer>
  );
}
