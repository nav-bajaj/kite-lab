"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { UserButton } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from "@/components/ui/sheet";
import { Home, Menu, Moon, Sun } from "lucide-react";
import { MobileSidebar } from "./mobile-sidebar";
import { UniverseSelector } from "./universe-selector";

const pathNames: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/performance": "Performance",
  "/rebalance": "Rebalance",
  "/trades": "Trades",
  "/admin": "Admin",
  "/account": "Account",
};

export function Navbar() {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();

  // eslint-disable-next-line security/detect-object-injection -- pathname is from Next's router (closed set of known route strings); pathNames is a module-level constant Record
  const pageName = pathNames[pathname] || "Dashboard";

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b bg-background px-4 lg:px-6">
      {/* Mobile menu button */}
      <Sheet>
        <SheetTrigger asChild>
          <Button variant="ghost" size="icon" className="lg:hidden">
            <Menu className="h-5 w-5" />
            <span className="sr-only">Toggle menu</span>
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="p-0 w-64">
          <SheetTitle className="sr-only">Navigation Menu</SheetTitle>
          <MobileSidebar />
        </SheetContent>
      </Sheet>

      {/* Page title */}
      <div className="flex-1">
        <h1 className="text-lg font-semibold">{pageName}</h1>
      </div>

      {/* Right cluster — portfolio selector + actions. The icon buttons each
          carry ~10px of transparent padding around their glyph, while the
          selector box and avatar are solid-edged. Kept at gap-2, that made the
          icon-to-icon gap (two paddings) read wider than the gaps next to the
          solid elements. Grouping the icon buttons with no gap between them
          collapses that double padding, so every visible glyph/edge sits an
          even ~18px apart. */}
      <div className="flex items-center gap-2">
        {/* Universe selector */}
        <div className="hidden sm:block">
          <UniverseSelector />
        </div>

        <div className="flex items-center">
          {/* Theme toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
            <span className="sr-only">Toggle theme</span>
          </Button>

          {/* Home — escape hatch back to the public marketing site. The
              dashboard is a separate app shell (sidebar nav), so signed-in
              users otherwise have no link out to the landing page. */}
          <Button variant="ghost" size="icon" asChild>
            <Link href="/" aria-label="Marketworks home">
              <Home className="h-5 w-5" />
            </Link>
          </Button>
        </div>

        {/* User menu — Clerk-managed avatar, profile, sign-out. On sign-out
            the middleware redirects unauthed users to /sign-in automatically. */}
        <UserButton appearance={{ elements: { avatarBox: "h-9 w-9" } }} />
      </div>
    </header>
  );
}
