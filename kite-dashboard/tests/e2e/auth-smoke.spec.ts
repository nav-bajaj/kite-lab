/**
 * Auth-stack E2E smoke (auth_stack_v2 H3.7) — must pass before cutover.
 *
 * Exercises the REAL flow end to end against the linked Supabase
 * project: route protection, the sign-in UI, email-OTP verification
 * (code obtained via the admin generateLink API — no inbox needed), the
 * session landing on /dashboard, and the admin-route gate for a
 * client-role user.
 *
 * Requires env:
 *   NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY (.env.local)
 *   SUPABASE_SERVICE_ROLE_KEY (exported by scripts/e2e-smoke.sh)
 */

import { test, expect } from "@playwright/test";
import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY ?? "";
const E2E_EMAIL = "e2e-client@marketworks.test";

test.skip(
  !SUPABASE_URL || !SERVICE_KEY,
  "SUPABASE_SERVICE_ROLE_KEY not set — run via scripts/e2e-smoke.sh",
);

function adminClient() {
  return createClient(SUPABASE_URL, SERVICE_KEY, {
    auth: { autoRefreshToken: false, persistSession: false },
  });
}

async function ensureE2eUser() {
  const admin = adminClient();
  const { data } = await admin.auth.admin.listUsers({
    page: 1,
    perPage: 200,
  });
  const existing = data?.users?.find((u) => u.email === E2E_EMAIL);
  if (existing) return existing.id;
  const { data: created, error } = await admin.auth.admin.createUser({
    email: E2E_EMAIL,
    email_confirm: true,
    app_metadata: { role: "client" },
  });
  if (error) throw error;
  return created.user.id;
}

async function freshEmailOtp(): Promise<string> {
  const admin = adminClient();
  const { data, error } = await admin.auth.admin.generateLink({
    type: "magiclink",
    email: E2E_EMAIL,
  });
  if (error) throw error;
  const otp = data.properties?.email_otp;
  if (!otp) throw new Error("generateLink returned no email_otp");
  return otp;
}

test.beforeAll(async () => {
  await ensureE2eUser();
});

test("unauthenticated /dashboard redirects to /sign-in", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/sign-in/);
});

test("unauthenticated /admin redirects to /sign-in", async ({ page }) => {
  await page.goto("/admin");
  await expect(page).toHaveURL(/\/sign-in/);
});

test("sign-in page renders both methods", async ({ page }) => {
  await page.goto("/sign-in");
  await expect(
    page.getByRole("button", { name: /continue with google/i }),
  ).toBeVisible();
  await expect(page.getByLabel("Email")).toBeVisible();
  await expect(
    page.getByRole("button", { name: /send sign-in code/i }),
  ).toBeVisible();
});

test("email OTP login lands on /dashboard; client is blocked from /admin", async ({
  page,
}) => {
  // Obtain a real OTP via the admin API (no inbox; SES sandbox would
  // reject sends to the .test address, and real sends to throwaway
  // domains would bounce and hurt SES reputation). The UI's code step
  // is reached via the ?email= deep link; verification is the real
  // GoTrue /verify call. NOTE: the send-click path stays manual until
  // SES production access + a real test inbox exist.
  const otp = await freshEmailOtp();
  await page.goto(`/sign-in?email=${encodeURIComponent(E2E_EMAIL)}`);
  await expect(page.getByText(/we sent a 6-digit code/i)).toBeVisible();
  await page.getByLabel("6-digit sign-in code").fill(otp);
  await page.getByRole("button", { name: /verify and continue/i }).click();

  // Full navigation carries the new session cookies.
  await page.waitForURL(/\/dashboard/, { timeout: 30_000 });

  // Session survives a fresh navigation (cookie-backed, middleware-read).
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/dashboard/);

  // R-022 edge mirror: client-role user bounced off /admin (to `/`).
  await page.goto("/admin");
  await expect(page).not.toHaveURL(/\/admin/);
});
