import { FloatingNav } from "@/components/marketing/floating-nav";
import { FooterPanel } from "@/components/marketing/footer-panel";
import { FlowGrid } from "@/components/marketing/flow-grid";

/**
 * Public legal surface layout (/terms, /privacy, /disclaimer). Mirrors the
 * /library layout: the layered marketing surface (floating glass nav,
 * quant-grid base, footer panel) so these pages read as part of the site.
 * `.mw-brand` scopes the brand role tokens + Outfit body font;
 * palette-transparent like every other surface.
 */
export default function LegalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="mw-brand relative flex min-h-screen flex-col overflow-hidden bg-surface-base">
      <FlowGrid />
      <FloatingNav />
      <div className="relative z-10 flex-1 pt-16 sm:pt-20">{children}</div>
      <div className="relative z-10 pb-6">
        <FooterPanel />
      </div>
    </div>
  );
}
