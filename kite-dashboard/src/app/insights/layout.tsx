import Link from "next/link";

export const metadata = {
  title: "Insights — Marketworks",
  description:
    "Quantitative market commentary on Indian equities — regime, stress, sector rotation, and historical analogs.",
};

const TABS = [
  { href: "/insights", label: "Pulse" },
  { href: "/insights/sectors", label: "Sectors" },
  { href: "/insights/analogs", label: "Analogs" },
  { href: "/insights/watchlists", label: "Watchlists" },
];

export default function InsightsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      {/*
        STRUCTURE-ONLY scaffold — visual design pending the broader design
        engine + content OS integration. Bare layout, system fonts, no
        custom typography or chart libraries yet.
      */}
      <header className="mb-6 border-b pb-4">
        <h1 className="text-2xl font-semibold">Marketworks Insights</h1>
        <p className="mt-1 text-sm text-neutral-600">
          Daily quantitative read on Indian equity markets. Educational
          content; not investment advice.
        </p>
        <nav className="mt-4 flex flex-wrap gap-3 text-sm">
          {TABS.map((t) => (
            <Link
              key={t.href}
              href={t.href}
              className="rounded border px-3 py-1 hover:bg-neutral-100 dark:hover:bg-neutral-900"
            >
              {t.label}
            </Link>
          ))}
        </nav>
      </header>

      {children}

      <footer className="mt-12 border-t pt-4 text-xs text-neutral-500">
        Educational commentary based on quantitative market data — not
        investment advice. Past patterns do not guarantee future outcomes.
      </footer>
    </div>
  );
}
