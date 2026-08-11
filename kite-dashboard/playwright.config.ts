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
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
