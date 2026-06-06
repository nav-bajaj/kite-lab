"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth, UserButton } from "@clerk/nextjs";
import { Menu, X } from "lucide-react";
import { INSIGHTS_ENABLED } from "@/lib/flags";

const LINKS = [
  { label: "Library", href: "/library" },
  ...(INSIGHTS_ENABLED ? [{ label: "Insights", href: "/insights" }] : []),
  { label: "Portfolios", href: "/dashboard" },
];

/**
 * Marketing top nav for the public brand surfaces (landing, /library, legal).
 * Wordmark + section links, with an auth-aware right side: sign-in / beta CTA
 * for signed-out visitors, dashboard link + account menu for signed-in users.
 * Defaults to the signed-out CTAs until Clerk loads (the common visitor case),
 * then swaps for signed-in users. Matches the guide's Reading Page board.
 *
 * Below `sm` the section links collapse behind a hamburger that toggles a
 * slide-down panel, so the same navigation is reachable on mobile — the CTA
 * alone left phone visitors with no way to reach Library/Portfolios.
 */
export function MarketingNav({ active }: { active?: string }) {
  const { isLoaded, isSignedIn } = useAuth();
  const showSignedIn = isLoaded && isSignedIn;
  const [open, setOpen] = useState(false);

  return (
    <nav className="border-b border-border bg-background">
      <div className="flex items-center justify-between px-6 py-5 sm:px-12">
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
                className="hidden text-base font-medium text-muted-foreground transition-colors hover:text-foreground sm:inline"
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

          <button
            type="button"
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
            className="-mr-1 inline-flex items-center justify-center rounded-md p-1.5 text-foreground transition-colors hover:bg-foreground/5 sm:hidden"
          >
            {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>

      {open && (
        <div className="border-t border-border px-6 py-2 sm:hidden">
          <div className="flex flex-col">
            {LINKS.map((link) => (
              <Link
                key={link.label}
                href={link.href}
                onClick={() => setOpen(false)}
                className={
                  link.label === active
                    ? "py-3 text-base font-medium text-foreground"
                    : "py-3 text-base font-medium text-muted-foreground transition-colors hover:text-foreground"
                }
              >
                {link.label}
              </Link>
            ))}
            {showSignedIn ? (
              <Link
                href="/dashboard"
                onClick={() => setOpen(false)}
                className="py-3 text-base font-medium text-muted-foreground transition-colors hover:text-foreground"
              >
                Dashboard
              </Link>
            ) : (
              <Link
                href="/sign-in"
                onClick={() => setOpen(false)}
                className="py-3 text-base font-medium text-muted-foreground transition-colors hover:text-foreground"
              >
                Sign in
              </Link>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}
