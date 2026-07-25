import Link from "next/link";
import { SignUp } from "@clerk/nextjs";

import { clerkAppearance } from "@/lib/clerk-appearance";
import { FlowGrid } from "@/components/marketing/flow-grid";

export default function SignUpPage() {
  return (
    <div className="mw-brand relative flex min-h-screen flex-col overflow-hidden bg-surface-base">
      <FlowGrid />
      <header className="relative z-10 px-6 py-5 sm:px-12">
        <Link
          href="/"
          className="text-2xl font-semibold tracking-tight text-primary"
        >
          marketworks
        </Link>
      </header>
      <div className="relative z-10 flex flex-1 flex-col items-center justify-center gap-8 px-6 pb-20">
        <div className="flex max-w-[420px] flex-col items-center gap-3 text-center">
          <h1 className="font-serif text-3xl font-medium text-foreground">
            Join the private beta
          </h1>
          <p className="text-[15px] leading-[1.55] text-muted-foreground">
            Free during beta. Access the model portfolios and the daily insight
            engine.
          </p>
        </div>
        <SignUp appearance={clerkAppearance} signInUrl="/sign-in" />
      </div>
    </div>
  );
}
