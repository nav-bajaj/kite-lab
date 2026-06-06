import { MarketingNav } from "@/components/marketing/marketing-nav";
import { MarketingFooter } from "@/components/marketing/marketing-footer";

/**
 * /library surface layout. Wraps the public content pages in the `.mw-brand`
 * scope (DESIGN.md §2.2 — brand role tokens + Outfit body font, light-locked
 * per §8.5) so every nested Tailwind/shadcn utility inherits the brand,
 * without affecting the authenticated dashboard.
 */
export default function LibraryLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="mw-brand flex min-h-screen flex-col bg-background">
      <MarketingNav active="Library" />
      <div className="flex-1">{children}</div>
      <MarketingFooter />
    </div>
  );
}
