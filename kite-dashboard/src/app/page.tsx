import { getSupabaseServerClient } from "@/lib/supabase/server";

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
  // cached static shell. Do not remove this call from the gated path — a
  // cached shell here would serve the wrong page to the wrong person.
  //
  // getClaims verifies the JWT locally against the project JWKS (ES256), so
  // this costs no auth-server round-trip on the marketing page.
  const supabase = await getSupabaseServerClient();
  const { data } = await supabase.auth.getClaims();
  const claims = data?.claims ?? null;

  const role = (claims as { app_metadata?: { role?: string } } | null)
    ?.app_metadata?.role;
  const userId = (claims as { sub?: string } | null)?.sub ?? null;

  if (siteMode() === "under_development" && role !== "admin") {
    return <ComingSoon />;
  }
  return <LandingPage userId={userId} />;
}
