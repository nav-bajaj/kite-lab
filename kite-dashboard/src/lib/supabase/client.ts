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
      // Session cookies are JS-readable by design (R-029). Cap their
      // lifetime to 7 days (library default: 400) as containment.
      { cookieOptions: { maxAge: 7 * 24 * 60 * 60 } },
    );
  }
  return client;
}
