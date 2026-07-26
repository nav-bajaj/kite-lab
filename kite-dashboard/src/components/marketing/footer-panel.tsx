import Link from "next/link";

import { INSIGHTS_ACCESS } from "@/lib/flags";
import { SectionPanel } from "./section-panel";

const FOOTER_LINKS = [
  { label: "Portfolios", href: "/portfolios" },
  { label: "Library", href: "/library" },
  ...(INSIGHTS_ACCESS === "all" ? [{ label: "Insights", href: "/insights" }] : []),
  { label: "Terms", href: "/terms" },
  { label: "Privacy", href: "/privacy" },
  { label: "Disclaimer", href: "/disclaimer" },
];

/**
 * Homepage footer as a deep inset card (homepage_visual_refresh) — the same
 * floating-panel language as the CTA/research sections, so the page closes on
 * a card rather than a plain full-bleed footer. Other marketing surfaces still
 * use the shared MarketingFooter until they migrate onto this layout.
 */
export function FooterPanel() {
  return (
    <SectionPanel variant="deep" className="py-10 sm:py-12">
      <div className="flex flex-col gap-8">
        <div className="flex flex-col justify-between gap-8 sm:flex-row sm:items-start">
          <div className="max-w-[440px]">
            <Link
              href="/"
              className="text-xl font-semibold tracking-tight text-surface-panel-deep-foreground"
            >
              marketworks
            </Link>
            <p className="mt-3 text-sm leading-[1.6] text-surface-panel-deep-foreground/65">
              Marketworks publishes educational research grounded in our own
              momentum portfolios and live insight engine. Nothing here is
              investment advice or a recommendation to buy or sell any security.
              Markets carry risk; past behaviour is not a guarantee of future
              results.
            </p>
          </div>
          <nav className="flex flex-wrap gap-x-8 gap-y-2.5 sm:justify-end">
            {FOOTER_LINKS.map((link) => (
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
        <div className="border-t border-surface-panel-deep-foreground/12 pt-5 text-sm text-surface-panel-deep-foreground/55">
          &copy; 2026 Marketworks Research &middot; SEBI Registered Research
          Analyst
        </div>
      </div>
    </SectionPanel>
  );
}
