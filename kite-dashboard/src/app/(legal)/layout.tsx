import { FloatingNav } from "@/components/marketing/floating-nav";
import { FooterPanel } from "@/components/marketing/footer-panel";
import { FlowGrid } from "@/components/marketing/flow-grid";
import { GatedFooter, GatedHeader } from "@/components/marketing/gated-chrome";
import { siteMode } from "@/lib/site-mode";

/**
 * Public legal surface layout (/terms, /privacy, /disclaimer). Mirrors the
 * /library layout: the layered marketing surface (floating glass nav,
 * quant-grid base, footer panel) so these pages read as part of the site.
 * `.mw-brand` scopes the brand role tokens + Outfit body font;
 * palette-transparent like every other surface.
 *
 * Under SITE_MODE=under_development the chrome swaps to the gated header/
 * footer: no nav links to gated routes, no "SEBI Registered" line. These
 * pages are statically prerendered, so the choice bakes at build time —
 * correct on Vercel because every env flip is a redeploy.
 */
export default function LegalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const gated = siteMode() === "under_development";
  return (
    <div className="mw-brand relative flex min-h-screen flex-col overflow-hidden bg-surface-base">
      <FlowGrid />
      {gated ? <GatedHeader /> : <FloatingNav />}
      <div className="relative z-10 flex-1 pt-16 sm:pt-20">{children}</div>
      <div className="relative z-10 pb-6">
        {gated ? <GatedFooter /> : <FooterPanel />}
      </div>
    </div>
  );
}
