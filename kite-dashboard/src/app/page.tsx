import { auth } from "@clerk/nextjs/server";

import { siteMode } from "@/lib/site-mode";
import { ComingSoon } from "@/components/marketing/coming-soon";
import { LandingPage } from "@/components/marketing/landing-page";

export async function generateMetadata() {
  if (siteMode() === "under_development") {
    return {
      title: "Marketworks",
      description: "Marketworks is under development.",
      robots: { index: false, follow: false },
    };
  }
  return {
    title: "Marketworks — Indian markets, the calm way",
    description:
      "Three ready-made momentum portfolios and a daily market read for Indian " +
      "stocks — built on years of quantitative research, not hunches. Process " +
      "over prediction. Currently in private beta.",
  };
}

export default async function Home() {
  // Reading the session unconditionally keeps this route dynamic: SITE_MODE
  // and the caller's role are evaluated per request, never baked into a
  // cached static shell. Do not remove the auth() call from the gated path.
  const { userId, sessionClaims } = await auth();
  const role = (
    sessionClaims as { metadata?: { role?: string } } | null
  )?.metadata?.role;

  if (siteMode() === "under_development" && role !== "admin") {
    return <ComingSoon />;
  }
  return <LandingPage userId={userId} />;
}
