"use client";

import Link from "next/link";
import { useAuth, UserButton } from "@clerk/nextjs";

const LINKS = [
  { label: "Library", href: "/library" },
  { label: "Insights", href: "/insights" },
  { label: "Portfolios", href: "/dashboard" },
];

/**
 * Marketing top nav for the public brand surfaces (landing + /library).
 * Wordmark + section links, with an auth-aware right side: sign-in / beta CTA
 * for signed-out visitors, dashboard link + account menu for signed-in users.
 * Defaults to the signed-out CTAs until Clerk loads (the common visitor case),
 * then swaps for signed-in users. Matches the guide's Reading Page board.
 */
export function MarketingNav({ active }: { active?: string }) {
  const { isLoaded, isSignedIn } = useAuth();
  const showSignedIn = isLoaded && isSignedIn;

  return (
    <nav className="flex items-center justify-between border-b border-border bg-background px-6 py-5 sm:px-12">
      <Link
        href="/"
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

      <div className="flex items-center gap-4">
        {showSignedIn ? (
          <>
            <Link
              href="/dashboard"
              className="text-base font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              Dashboard
            </Link>
            <UserButton />
          </>
        ) : (
          <>
            <Link
              href="/sign-in"
              className="hidden text-base font-medium text-muted-foreground transition-colors hover:text-foreground sm:inline"
            >
              Sign in
            </Link>
            <Link
              href="/sign-up"
              className="rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90"
            >
              Get beta access
            </Link>
          </>
        )}
      </div>
    </nav>
  );
}
