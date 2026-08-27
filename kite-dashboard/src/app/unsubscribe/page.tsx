import { UnsubscribeCard } from "@/components/marketing/unsubscribe-card";

export const metadata = {
  title: "Unsubscribe — Marketworks",
  robots: { index: false, follow: false },
};

/**
 * Public unsubscribe landing page (tasks/email_channel Phase 2).
 *
 * MUST stay in PUBLIC_WHEN_GATED (src/lib/site-mode.ts) — the site gate
 * would otherwise redirect every unsubscribe link in every email to the
 * home page, which is both a broken promise and a compliance failure.
 *
 * The visible link in an email points here rather than straight at the
 * API so the reader gets a confirmation instead of a bare JSON body.
 * One-click unsubscribe (RFC 8058) bypasses this page and POSTs directly
 * to the API, which is what mail clients expect.
 */
export default async function UnsubscribePage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const { token } = await searchParams;
  return <UnsubscribeCard token={token ?? ""} />;
}
