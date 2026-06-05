import Link from "next/link";

const LINKS = [
  { label: "Library", href: "/library" },
  { label: "Insights", href: "/insights" },
  { label: "Portfolios", href: "/" },
];

/**
 * Marketing top nav for the public brand surfaces (/library now; landing +
 * sign-up later). Wordmark + section links + sign-in. Matches the guide's
 * Reading Page board: mist bar, lichen wordmark, hairline bottom border.
 */
export function MarketingNav({ active }: { active?: string }) {
  return (
    <nav className="flex items-center justify-between border-b border-border bg-background px-6 py-5 sm:px-12">
      <Link
        href="/library"
        className="text-2xl font-semibold tracking-tight text-primary"
      >
        marketworks
      </Link>

      <div className="hidden items-center gap-8 sm:flex">
        {LINKS.map((link) => (
          <Link
            key={link.label}
            href={link.href}
            className={
              link.label === active
                ? "text-base font-medium text-foreground"
                : "text-base font-medium text-muted-foreground transition-colors hover:text-foreground"
            }
          >
            {link.label}
          </Link>
        ))}
      </div>

      <Link
        href="/sign-in"
        className="rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90"
      >
        Sign in
      </Link>
    </nav>
  );
}
