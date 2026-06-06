// Build-time feature flags. Read from NEXT_PUBLIC_* so client components and
// middleware resolve the same value.
//
// INSIGHTS_ENABLED gates the /insights surface. OFF by default: the insight
// engine reads data files (indices history + NSE-500 constituent prices) that
// are not yet provisioned on the production backend, so /insights 500s in
// prod. While gated, the nav links are hidden and /insights* redirects to
// /dashboard. Enable by setting NEXT_PUBLIC_INSIGHTS_ENABLED=true — locally
// (dev has the data) and in production once the data-provisioning task lands.
// See tasks/design_system/RESULTS.md (founder action items).
export const INSIGHTS_ENABLED =
  process.env.NEXT_PUBLIC_INSIGHTS_ENABLED === "true";
