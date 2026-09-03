"use client";

import Link from "next/link";
import { LogOut, User as UserIcon } from "lucide-react";

import { useSupabaseAuth } from "@/contexts/supabase-auth-context";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

/**
 * Signed-in user menu — replaces Clerk's <UserButton/> (auth_stack_v2
 * F2.6). Avatar image comes from user_metadata (Google profile photo when
 * present); fallback is the email's first letter. This is the dashboard's
 * only sign-out affordance.
 */
export function UserMenu() {
  const { user, signOut } = useSupabaseAuth();
  if (!user) return null;

  const meta = user.user_metadata as
    | { avatar_url?: string; full_name?: string }
    | undefined;
  const email = user.email ?? "";
  const name = meta?.full_name ?? email;
  const initial = (name || email || "?").charAt(0).toUpperCase();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="rounded-full outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
        aria-label="Account menu"
      >
        <Avatar className="h-9 w-9">
          {meta?.avatar_url ? (
            <AvatarImage src={meta.avatar_url} alt={name} />
          ) : null}
          <AvatarFallback className="bg-primary/10 text-sm font-semibold text-primary">
            {initial}
          </AvatarFallback>
        </Avatar>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col gap-0.5">
            {meta?.full_name ? (
              <span className="truncate text-sm font-medium">
                {meta.full_name}
              </span>
            ) : null}
            <span className="truncate text-xs text-muted-foreground">
              {email}
            </span>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href="/account">
            <UserIcon className="h-4 w-4" />
            Account
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => void signOut()}>
          <LogOut className="h-4 w-4" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
