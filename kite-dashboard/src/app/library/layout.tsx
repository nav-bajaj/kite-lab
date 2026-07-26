import { FloatingNav } from "@/components/marketing/floating-nav";
import { FooterPanel } from "@/components/marketing/footer-panel";
import { FlowGrid } from "@/components/marketing/flow-grid";

/**
 * /library surface layout. Wraps the public content pages in the `.mw-brand`
 * scope (brand role tokens + Outfit body font) on the layered marketing
 * surface — floating glass nav, quant-grid base, footer panel — matching the
 * redesigned homepage. Palette-transparent: all six palettes (incl. Midnight)
 * flow through the tokens.
 */
export default function LibraryLayout({
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
