// Build-time feature flags. Read from NEXT_PUBLIC_* so client components and
// middleware resolve the same value.
//
// INSIGHTS_ACCESS gates the /insights surface as a tri-state access mode:
//   "off"   — surface hidden; /insights* redirects to /dashboard (default).
//   "admin" — surface reachable only by admin-role sessions; clients bounce
//             to /dashboard. Marketing surfaces (public) do NOT advertise it.
//   "all"   — any signed-in user (today's original behavior); marketing links
//             appear.
//
// Why tri-state: the insight engine reads data panels (indices history +
// NSE-500 constituent prices) that are provisioned on Railway but the surface
// launches to admins first (compliance sandbox) before any public flip. See
// tasks/insights_v2/PLAN.md (Phase A).
//
// Backward compatibility: the legacy binary NEXT_PUBLIC_INSIGHTS_ENABLED=true
// maps to "all" so existing environments keep working without a rename.
export type InsightsAccess = "off" | "admin" | "all";

function resolveInsightsAccess(): InsightsAccess {
  const raw = (process.env.NEXT_PUBLIC_INSIGHTS_ACCESS ?? "").toLowerCase();
  if (raw === "off" || raw === "admin" || raw === "all") return raw;
  // Legacy flag: ENABLED=true ⇒ all. Anything else ⇒ off.
  if (process.env.NEXT_PUBLIC_INSIGHTS_ENABLED === "true") return "all";
  return "off";
}

export const INSIGHTS_ACCESS: InsightsAccess = resolveInsightsAccess();

// Derived boolean kept for any consumer that only cares whether the surface
// exists at all (not who can see it). True unless access is "off".
export const INSIGHTS_ENABLED = INSIGHTS_ACCESS !== "off";
