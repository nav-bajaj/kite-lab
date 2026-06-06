import Link from "next/link";
import { INSIGHTS_ENABLED } from "@/lib/flags";

const FOOTER_LINKS = [
  { label: "Library", href: "/library" },
  ...(INSIGHTS_ENABLED ? [{ label: "Insights", href: "/insights" }] : []),
  { label: "Terms", href: "/terms" },
  { label: "Privacy", href: "/privacy" },
  { label: "Disclaimer", href: "/disclaimer" },
];

/** Shared footer for the public marketing surfaces (landing + /library). */
export function MarketingFooter() {
  return (
    <footer className="border-t border-border px-6 py-12 sm:px-12">
      <div className="mx-auto flex max-w-[1080px] flex-col gap-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <Link
            href="/"
            className="text-xl font-semibold tracking-tight text-primary"
          >
            marketworks
          </Link>
          <div className="flex flex-wrap gap-x-6 gap-y-2">
            {FOOTER_LINKS.map((link) => (
              <Link
                key={link.label}
                href={link.href}
                className="text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                {link.label}
              </Link>
            ))}
          </div>
        </div>
        <p className="max-w-[680px] text-sm leading-[1.55] text-muted-foreground">
          Marketworks publishes educational research grounded in our own
          momentum portfolios and live insight engine. Nothing here is
          investment advice or a recommendation to buy or sell any security.
          Markets carry risk; past behaviour is not a guarantee of future
          results.
        </p>
      </div>
    </footer>
  );
}
