import { ConfirmCard } from "@/components/marketing/confirm-card";

export const metadata = {
  title: "Confirm your email — Marketworks",
  robots: { index: false, follow: false },
};

/**
 * Double opt-in landing page (tasks/email_channel Phase 2).
 *
 * Inert while WAITLIST_DOUBLE_OPT_IN is false — nothing links here today.
 * It exists so flipping that flag needs no new code, and so the route in
 * the middleware allowlists is not a dangling reference.
 *
 * Like /unsubscribe, this must stay in BOTH allowlists: isPublicRoute in
 * src/middleware.ts and PUBLIC_WHEN_GATED in src/lib/site-mode.ts.
 */
export default async function ConfirmPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const { token } = await searchParams;
  return <ConfirmCard token={token ?? ""} />;
}
