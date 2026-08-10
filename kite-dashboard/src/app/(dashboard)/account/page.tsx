"use client";

import { LogOut, Mail, ShieldCheck } from "lucide-react";

import { useSupabaseAuth } from "@/contexts/supabase-auth-context";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { GoogleMark } from "@/components/auth/google-mark";

/**
 * Account page (auth_stack_v2 F2.4) — replaces Clerk's <UserProfile/>.
 * Deliberately minimal: identity summary, sign-in methods, sign out.
 */
export default function AccountPage() {
  const { user, role, signOut, isLoaded } = useSupabaseAuth();

  if (!isLoaded || !user) return null;

  const meta = user.user_metadata as
    | { avatar_url?: string; full_name?: string }
    | undefined;
  const email = user.email ?? "";
  const name = meta?.full_name ?? email;
  const initial = (name || email || "?").charAt(0).toUpperCase();
  const providers = (user.app_metadata?.providers as string[] | undefined) ?? [
    user.app_metadata?.provider ?? "email",
  ];

  return (
    <div className="flex justify-center py-4">
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <CardTitle className="font-serif text-2xl font-medium">
            Account
          </CardTitle>
          <CardDescription>
            Your Marketworks sign-in and profile details.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <div className="flex items-center gap-4">
            <Avatar className="h-14 w-14">
              {meta?.avatar_url ? (
                <AvatarImage src={meta.avatar_url} alt={name} />
              ) : null}
              <AvatarFallback className="bg-primary/10 text-lg font-semibold text-primary">
                {initial}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0">
              {meta?.full_name ? (
                <p className="truncate font-medium text-foreground">
                  {meta.full_name}
                </p>
              ) : null}
              <p className="truncate text-sm text-muted-foreground">{email}</p>
              {role === "admin" ? (
                <p className="mt-1 inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                  <ShieldCheck className="h-3 w-3" /> Admin
                </p>
              ) : null}
            </div>
          </div>

          <Separator />

          <div className="flex flex-col gap-2">
            <p className="text-sm font-medium text-foreground">
              Sign-in methods
            </p>
            <div className="flex flex-wrap gap-2">
              {providers.map((p) => (
                <span
                  key={p}
                  className="inline-flex items-center gap-1.5 rounded-md border border-border bg-muted px-2.5 py-1 text-xs font-medium text-foreground"
                >
                  {p === "google" ? (
                    <GoogleMark className="size-3.5" />
                  ) : (
                    <Mail className="h-3.5 w-3.5 text-muted-foreground" />
                  )}
                  {p === "google" ? "Google" : "Email code"}
                </span>
              ))}
            </div>
            <p className="text-xs leading-[1.5] text-muted-foreground">
              Sign in with Google or a one-time email code — both connect to
              this same account via {email}.
            </p>
          </div>

          <Separator />

          <div>
            <Button variant="outline" onClick={() => void signOut()}>
              <LogOut className="h-4 w-4" /> Sign out
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
