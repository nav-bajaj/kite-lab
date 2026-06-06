import Link from "next/link";
import { SignIn } from "@clerk/nextjs";

import { clerkAppearance } from "@/lib/clerk-appearance";

export default function SignInPage() {
  return (
    <div className="mw-brand flex min-h-screen flex-col bg-background">
      <header className="px-6 py-5 sm:px-12">
        <Link
          href="/"
          className="text-2xl font-semibold tracking-tight text-primary"
        >
          marketworks
        </Link>
      </header>
      <div className="flex flex-1 flex-col items-center justify-center gap-8 px-6 pb-20">
        <h1 className="font-serif text-3xl font-medium text-foreground">
          Welcome back
        </h1>
        <SignIn appearance={clerkAppearance} signUpUrl="/sign-up" />
      </div>
    </div>
  );
}
