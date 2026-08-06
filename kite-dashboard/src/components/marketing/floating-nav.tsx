"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth, UserButton } from "@clerk/nextjs";
import { Menu, X } from "lucide-react";

import { INSIGHTS_ACCESS } from "@/lib/flags";
import { cn } from "@/lib/utils";

// Same public link set as the legacy MarketingNav — Insights only advertised on
// a full public launch (access=all).
const LINKS = [
  { label: "Portfolios", href: "/portfolios" },
  { label: "Library", href: "/library" },
  ...(INSIGHTS_ACCESS === "all"
    ? [{ label: "Insights", href: "/insights" }]
    : []),
];

/**
 * Floating glass-pill marketing nav (homepage_visual_refresh, Acctual
 * reference). Fixed, centred, translucent white over the layered base so it
 * picks up whichever panel scrolls under it; tightens toward the top edge on
 * scroll. Auth-aware right side (sign-in / beta CTA, or dashboard + account),
 * with a hamburger sheet below sm. Used on the redesigned homepage; other
 * marketing pages migrate to it in Phase E.
 */
export function FloatingNav() {
  const { isLoaded, isSignedIn } = useAuth();
  const showSignedIn = isLoaded && isSignedIn;
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled((window.scrollY || 0) > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div
      className={cn(
        "fixed inset-x-0 top-0 z-50 flex justify-center px-4 transition-[padding] duration-300 ease-expo sm:px-6",
        scrolled ? "pt-2" : "pt-4 sm:pt-5",
      )}
    >
      <nav className="w-full max-w-[1080px] rounded-3xl border border-foreground/8 bg-card/80 shadow-sm backdrop-blur-md">
        {/* Fixed row height so the bar is identical signed-in vs signed-out
            (the beta CTA is taller than the avatar/Dashboard link). */}
        <div className="grid h-14 grid-cols-[auto_1fr_auto] items-center px-4 sm:grid-cols-[1fr_auto_1fr] sm:px-5">
          <Link
            href="/"
            className="inline-flex items-center justify-self-start text-xl font-semibold leading-none tracking-tight text-primary"
          >
            marketworks
          </Link>

          <div className="hidden items-center justify-self-center gap-8 sm:flex">
            {LINKS.map((link) => (
              <Link
                key={link.label}
                href={link.href}
                className="text-sm font-medium text-foreground/75 transition-colors hover:text-primary"
              >
                {link.label}
              </Link>
            ))}
          </div>

          {/* justify-end INSIDE the flex as well as justify-self-end on the
              grid item: with narrow signed-in content (avatar + burger) the
              1fr track is wider than the cluster, and only an inner
              justify-end pins the children to the right edge. */}
          <div className="flex items-center justify-end justify-self-end gap-2 sm:gap-3">
            {/* Palette picker — signed-out choices persist per device;
                signed-in choices roam via Clerk (PaletteSync). */}
            {showSignedIn ? (
              <>
                <Link
                  href="/dashboard"
                  className="hidden px-2 text-sm font-medium text-foreground/75 transition-colors hover:text-primary sm:inline"
                >
                  Dashboard
                </Link>
                <UserButton />
              </>
            ) : (
              <>
                <Link
                  href="/sign-in"
                  className="hidden px-2 text-sm font-medium text-foreground/75 transition-colors hover:text-primary sm:inline"
                >
                  Sign in
                </Link>
                <Link
                  href="/sign-up"
                  className="whitespace-nowrap rounded-full bg-primary px-4 py-2 text-[13px] font-semibold text-primary-foreground sm:px-5 sm:py-2.5 sm:text-sm transition-[transform,box-shadow] duration-200 ease-expo hover:-translate-y-px hover:shadow-[0_6px_18px_-6px_color-mix(in_oklab,var(--primary)_50%,transparent)]"
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
              className="inline-flex items-center justify-center rounded-full p-2 text-foreground transition-colors hover:bg-foreground/5 sm:hidden"
            >
              {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>

        {open && (
          <div className="border-t border-border/60 px-6 py-2 sm:hidden">
            <div className="flex flex-col">
              {LINKS.map((link) => (
                <Link
                  key={link.label}
                  href={link.href}
                  onClick={() => setOpen(false)}
                  className="py-2.5 text-sm font-medium text-foreground/75 transition-colors hover:text-primary"
                >
                  {link.label}
                </Link>
              ))}
              <Link
                href={showSignedIn ? "/dashboard" : "/sign-in"}
                onClick={() => setOpen(false)}
                className="py-2.5 text-sm font-medium text-foreground/75 transition-colors hover:text-primary"
              >
                {showSignedIn ? "Dashboard" : "Sign in"}
              </Link>
            </div>
          </div>
        )}
      </nav>
    </div>
  );
}
