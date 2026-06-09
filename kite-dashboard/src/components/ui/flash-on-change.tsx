import { cn } from "@/lib/utils";

interface FlashOnChangeProps {
  // Numeric trigger: when it changes, the element remounts and re-animates.
  value: number;
  children: React.ReactNode;
  className?: string;
}

// Subtly highlights its content whenever `value` changes, so a live
// price/P&L update reads as a smooth transition rather than a jarring
// instant swap. The `key` makes React remount the element only when the
// value changes, which restarts the one-shot CSS animation — no hooks,
// effects, or setState, so it never triggers cascading renders. It flashes
// the *background* (not the text colour) so it composes with P&L red/green.
// (A single subtle flash also plays on first mount; that's intentional.)
export function FlashOnChange({ value, children, className }: FlashOnChangeProps) {
  return (
    <span
      key={value}
      className={cn("rounded-sm animate-value-flash", className)}
    >
      {children}
    </span>
  );
}
