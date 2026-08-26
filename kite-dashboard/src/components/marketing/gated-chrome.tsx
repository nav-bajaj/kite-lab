import Link from "next/link";

import { SectionPanel } from "./section-panel";

/**
 * Minimal chrome for the under-development site mode (tasks/site_gate).
 * No nav links, no sign-in link, and no "SEBI Registered Research Analyst"
 * line — the registration application is pending, so that claim must not
 * render anywhere in gated mode.
 */

const GATED_FOOTER_LINKS = [
  { label: "Terms", href: "/terms" },
  { label: "Privacy", href: "/privacy" },
  { label: "Disclaimer", href: "/disclaimer" },
];

export function GatedHeader() {
  return (
    <header className="relative z-20 mx-auto flex w-full max-w-[1140px] items-center px-6 pt-8">
      <Link
        href="/"
        className="text-xl font-semibold tracking-tight text-foreground"
      >
        marketworks
      </Link>
    </header>
  );
}

export function GatedFooter() {
  return (
    <SectionPanel variant="deep" className="py-8 sm:py-10">
      <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-center">
        <div className="text-sm text-surface-panel-deep-foreground/55">
          &copy; 2026 Marketworks Research
        </div>
        <nav className="flex flex-wrap gap-x-8 gap-y-2.5">
          {GATED_FOOTER_LINKS.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              className="text-sm text-surface-panel-deep-foreground/70 transition-colors hover:text-surface-panel-deep-foreground"
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </div>
    </SectionPanel>
  );
}
