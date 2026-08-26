import { FlowGrid } from "@/components/marketing/flow-grid";
import { SectionPanel } from "@/components/marketing/section-panel";
import { WaitlistForm } from "@/components/marketing/waitlist-form";
import { GatedFooter, GatedHeader } from "@/components/marketing/gated-chrome";

/**
 * The under-development home page (tasks/site_gate). This is the ONLY page
 * a non-admin visitor can see while SITE_MODE=under_development: wordmark,
 * a short note, the waitlist form, and legal links. No nav, no sign-in
 * link, no product surface.
 *
 * PLACEHOLDER COPY: the founder writes the final wording. Keep the
 * register neutral — say the platform is under development; do not make
 * affirmative claims about SEBI registration status.
 */
export function ComingSoon() {
  return (
    <div className="mw-brand relative flex min-h-screen flex-col overflow-hidden bg-surface-base">
      <FlowGrid />

      <GatedHeader />

      <main className="relative z-10 flex flex-1 items-center">
        <SectionPanel variant="mist" className="my-16">
          <div className="mx-auto flex max-w-[640px] flex-col items-start gap-6 py-8">
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">
              Under development
            </span>
            <h1 className="font-serif text-[2.5rem] font-medium leading-[1.08] tracking-[-0.02em] text-foreground sm:text-[3.25rem]">
              Something calm is taking shape.
            </h1>
            <p className="text-lg leading-[1.65] text-muted-foreground">
              Marketworks is a research platform for Indian equities, currently
              under development. Leave your email and we&apos;ll let you know
              when we launch.
            </p>
            <WaitlistForm />
          </div>
        </SectionPanel>
      </main>

      <div className="relative z-10 pb-6">
        <GatedFooter />
      </div>
    </div>
  );
}
