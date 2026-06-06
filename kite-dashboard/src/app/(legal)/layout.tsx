import { MarketingNav } from "@/components/marketing/marketing-nav";
import { MarketingFooter } from "@/components/marketing/marketing-footer";

/**
 * Public legal surface layout (/terms, /privacy, /disclaimer). Mirrors the
 * /library layout: the same brand-scoped top nav + footer so these pages are
 * no longer orphaned — visitors who land on a legal page can navigate back to
 * the rest of the site. `.mw-brand` scopes the brand role tokens + Outfit body
 * font (light-locked per DESIGN.md §8.5) without touching the authed dashboard.
 */
export default function LegalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="mw-brand flex min-h-screen flex-col bg-background">
      <MarketingNav />
      <div className="flex-1">{children}</div>
      <MarketingFooter />
    </div>
  );
}
