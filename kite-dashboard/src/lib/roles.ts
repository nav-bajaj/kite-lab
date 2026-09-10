/**
 * App roles, as carried in the Supabase JWT's `app_metadata.role`.
 *
 * `app_metadata` is server-controlled (set via the Supabase admin API);
 * `user_metadata` is end-user-editable and is never consulted here or in
 * the backend (SI-1 in tasks/auth_stack_v2/PLAN.md).
 *
 * Three roles, and the distinction between the last two is the point:
 *
 *   admin    — operates the platform. Sees /admin, all 7 universes, and
 *              every mutation/engine endpoint.
 *   preview  — may pass the under-development site gate (R-028) and
 *              nothing more. Gets exactly the client product surface.
 *              For named, time-boxed access: hiring candidates, design
 *              partners, anyone being shown the product before launch.
 *   client   — an ordinary beta user. Blocked entirely while the site is
 *              gated.
 *
 * These checks are UX routing only. The FastAPI backend verifies the same
 * token and enforces the real gates independently (`GATE_ROLES`,
 * `require_admin`, `check_universe_access` in kite-api/app/auth.py) —
 * deliberately, because R-019 (Next.js middleware-bypass CVEs) means one
 * layer is not enough.
 */
export type AppRole = "admin" | "preview" | "client";

/** Anything unrecognised degrades to `client` — a bad role string must
 *  never accidentally land as a privileged one. */
export function parseRole(raw: unknown): AppRole {
  return raw === "admin" || raw === "preview" ? raw : "client";
}

/** Read the app role out of a verified JWT claims object. */
export function roleFromClaims(claims: unknown): AppRole {
  const meta = (claims as { app_metadata?: { role?: unknown } } | null)
    ?.app_metadata;
  return parseRole(meta?.role);
}

/**
 * May this role see the product while SITE_MODE=under_development?
 *
 * Passing the gate and operating the platform were the same predicate
 * until 2026-09-10. They are two different questions: keep asking this
 * one with `canPassGate` and the other with `role === "admin"`, and never
 * collapse them back together.
 */
export function canPassGate(role: AppRole): boolean {
  return role === "admin" || role === "preview";
}

/**
 * May this role see /insights while NEXT_PUBLIC_INSIGHTS_ACCESS="admin"?
 *
 * A SEPARATE question from canPassGate, deliberately, even though the two
 * answer identically today. INSIGHTS_ACCESS is not the SEBI gate: it is
 * the insight engine's own pre-publication hold (see @/lib/flags), and it
 * will still be "admin" for some window after SITE_MODE is lifted at
 * launch. If this just called canPassGate, that window is exactly when a
 * preview holder would stop being equivalent to a client and start
 * holding a durable entitlement nobody granted them — a hiring
 * conversation turning into standing access to the surface being held
 * back on compliance grounds.
 *
 * So: when the gate lifts, this is a one-line decision someone has to
 * make on purpose. The other half of the control is in
 * docs/security/preview-access.md — every outstanding preview grant is
 * revoked as part of the ungate, because the role means something
 * different afterwards.
 */
export function canSeeInsightsSandbox(role: AppRole): boolean {
  return role === "admin" || role === "preview";
}
