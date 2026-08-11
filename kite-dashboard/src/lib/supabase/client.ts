"use client";

import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";

let client: SupabaseClient | undefined;

/** Browser Supabase client (singleton — one GoTrue instance per tab). */
export function getSupabaseBrowserClient(): SupabaseClient {
  if (!client) {
    client = createBrowserClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      // Session cookies are JS-readable by design (R-029). Rolling
      // 30-day inactivity window (library default: 400 days): every
      // visit re-stamps the cookie, so active users never re-login;
      // dormant sessions die within a month. Founder decision
      // 2026-08-11 (ease-of-use vs the R-029 containment default of 7d).
      { cookieOptions: { maxAge: 30 * 24 * 60 * 60 } },
    );
  }
  return client;
}
