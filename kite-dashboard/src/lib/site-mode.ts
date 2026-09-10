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
// SITE_MODE is server-only AND siteMode() fails OPEN — unset reads as
// "live". Failing open is right for a gate (a misconfigured deploy must not
// lock everyone out of their own product) and wrong for the one other thing
// this function now decides: whether FooterPanel prints "SEBI Registered
// Research Analyst", a claim that is not true yet.
//
// Those two combine badly. One `"use client"` on any consumer pulls this
// module into the client bundle, where Next inlines `process.env.SITE_MODE`
// as undefined; `gated` silently becomes false and the claim comes back with
// no error, no type failure and no failing test.
//
// So make that mistake loud. React's `server-only` package would turn it into
// a build error, which is strictly better, but costs a dependency for a
// hypothetical — this throws on first import in a browser instead, which
// surfaces the moment any marketing page renders in dev. Server runtimes
// (middleware, server components, prerender) have no `window` and never
// reach it.
if (typeof window !== "undefined") {
  throw new Error(
    "site-mode.ts is server-only: SITE_MODE is not exposed to the browser, " +
      "so a client-side siteMode() would report 'live' and un-gate the " +
      "pending-registration claim. Read it in a server component instead.",
  );
}

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
// for non-admin visitors.
//
// Matching lives HERE rather than in the middleware because it must not
// depend on any auth library's route matcher — the gate outlived Clerk and
// should outlive whatever comes next. To open /library later, add it to
// GATED_PREFIXES: one line, nothing else changes.
const GATED_EXACT = new Set([
  "/",            // coming-soon page (admins see the real landing)
  "/terms",
  "/privacy",
  "/disclaimer",
  // .txt is not in the middleware matcher's static-asset exclusions, so
  // robots.txt needs an explicit entry — crawlers must reach it for the
  // deindexing strategy (see robots.ts) to work.
  "/robots.txt",
  // Email consent pages. Their only credential is the token in the URL and
  // they MUST stay reachable while gated — otherwise every unsubscribe link
  // in every email redirects to "/", which is a compliance failure rather
  // than merely a broken link. /confirm is inert under single opt-in but is
  // listed now so flipping that flag needs no other change.
  "/unsubscribe",
  "/confirm",
]);

const GATED_PREFIXES = [
  "/sign-in",     // includes /sign-in/factor-one, sso-callback, etc.
  "/auth",        // OAuth code-exchange hop; hit before a session exists
];

export function isGateOpenPath(path: string): boolean {
  return (
    GATED_EXACT.has(path) ||
    GATED_PREFIXES.some((b) => path === b || path.startsWith(b + "/"))
  );
}
