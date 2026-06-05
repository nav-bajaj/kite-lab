import Link from "next/link";

import { MarketingNav } from "@/components/library/MarketingNav";

/**
 * /library surface layout. Wraps the public content pages in the `.mw-brand`
 * scope (DESIGN.md §2.2 — brand role tokens + Outfit body font, light-locked
 * per §8.5) so every nested Tailwind/shadcn utility inherits the brand,
 * without affecting the authenticated dashboard. Adds the marketing nav +
 * disclaimer footer that frame every reading page.
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
      <footer className="border-t border-border px-6 py-10 sm:px-12">
        <div className="mx-auto flex max-w-[680px] flex-col gap-2 text-sm text-muted-foreground">
          <span className="font-semibold text-primary">marketworks</span>
          <p>
            Educational content grounded in our own momentum portfolios and
            live insight engine. Not investment advice. See{" "}
            <Link href="/disclaimer" className="underline hover:text-foreground">
              disclaimer
            </Link>
            .
          </p>
        </div>
      </footer>
    </div>
  );
}
