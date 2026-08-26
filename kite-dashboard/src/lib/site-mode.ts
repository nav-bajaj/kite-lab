/**
 * Site-wide access mode (tasks/site_gate).
 *
 * While the SEBI Research Analyst application is pending, the public site
 * shows only the under-development page; every other route is admin-only.
 *
 * SITE_MODE is deliberately a SERVER-side env var (not NEXT_PUBLIC_*): it
 * never enters client bundles, and middleware/server components read it per
 * request via this function rather than capturing it at module scope.
 * Unset defaults to "live" so other deployments (a future beta subdomain)
 * behave normally; the production Vercel project sets
 * SITE_MODE=under_development explicitly. Flipping the var still requires a
 * redeploy (Vercel env changes only apply to new builds).
 */
export type SiteMode = "live" | "under_development";

export function siteMode(): SiteMode {
  return process.env.SITE_MODE === "under_development"
    ? "under_development"
    : "live";
}

// Metadata fragment for pages that stay reachable while gated: keep them
// out of search indexes under the coming-soon brand state.
export function gatedRobots(): { robots?: { index: boolean; follow: boolean } } {
  return siteMode() === "under_development"
    ? { robots: { index: false, follow: false } }
    : {};
}

// Routes that stay reachable while gated. Everything else redirects to "/"
// for non-admin visitors. To open /library later, add "/library(.*)" here —
// one line, nothing else changes.
export const PUBLIC_WHEN_GATED = [
  "/", // coming-soon page (admins see the real landing)
  "/terms",
  "/privacy",
  "/disclaimer",
  "/sign-in(.*)", // includes /sign-in/factor-one, /sign-in/sso-callback
];
