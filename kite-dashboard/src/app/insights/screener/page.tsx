import { getScreener } from "@/lib/insights-api";
import { ScreenerClient } from "./_client";

export const dynamic = "force-dynamic";
export const revalidate = 900;

export const metadata = {
  title: "Screener — Marketworks Insights",
  description:
    "Decision-support data on every NSE 500 stock — relative strength, trend and momentum scores, extension and volume state. Educational, not recommendations.",
};

interface PageProps {
  searchParams: Promise<{ date?: string }>;
}

export default async function ScreenerPage({ searchParams }: PageProps) {
  const { date } = await searchParams;
  const { asof, data_available, rows } = await getScreener(date);

  if (!data_available || rows.length === 0) {
    return (
      <main className="flex flex-col gap-4">
        <h2 className="font-serif text-2xl font-medium tracking-[-0.01em] text-foreground">
          NSE 500 screener
        </h2>
        <p className="max-w-2xl text-[14px] leading-[1.6] text-muted-foreground">
          Stock-level data isn&apos;t available for this snapshot yet. Pick a
          more recent date, or check back once the daily panel has been
          provisioned.
        </p>
      </main>
    );
  }

  return <ScreenerClient rows={rows} asof={asof} />;
}
