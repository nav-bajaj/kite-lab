import { defineConfig } from "@playwright/test";

/**
 * E2E smoke for the auth stack (auth_stack_v2 H3.7).
 * Run via `npm run test:e2e` — the wrapper script exports the Supabase
 * service-role key from the CLI before invoking Playwright.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 60_000,
  retries: 0,
  reporter: [["list"]],
  use: {
    // Dedicated E2E port: 3000 is contested by other dev servers
    // (e.g. the design-studies worktree session) and a stale server
    // there silently fails the suite against old code. The email-OTP
    // flow doesn't touch the OAuth redirect allowlist, so the port is
    // free to differ from the Supabase-registered localhost:3000.
    baseURL: "http://localhost:3100",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npm run dev -- -p 3100",
    url: "http://localhost:3100",
    reuseExistingServer: false,
    timeout: 60_000,
    // The dev server never needs the admin key the spec's Node side
    // holds — blank it in the child process (security-reviewer #11).
    env: { SUPABASE_SERVICE_ROLE_KEY: "" },
  },
});
