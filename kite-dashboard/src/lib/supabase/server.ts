import { cookies } from "next/headers";
import { createServerClient } from "@supabase/ssr";

/**
 * Server-side Supabase client for Server Components and route handlers.
 * Note: `setAll` is a no-op failure inside Server Components (cookies are
 * read-only there) — middleware owns session refresh, so that's fine.
 */
export async function getSupabaseServerClient() {
  const cookieStore = await cookies();
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      // R-029 containment — see src/lib/supabase/client.ts.
      cookieOptions: { maxAge: 7 * 24 * 60 * 60 },
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options),
            );
          } catch {
            // Server Component — middleware handles refresh.
          }
        },
      },
    },
  );
}
