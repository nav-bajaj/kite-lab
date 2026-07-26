import type { ReactNode } from "react";
import Image from "next/image";

import { cn } from "@/lib/utils";
import { MarketingCard } from "./marketing-card";
import { Halftone } from "./halftone";

/**
 * A card that leads with a graphic — the second card primitive (DESIGN.md §2.5).
 * Either an `image` (a self-hosted grain illustration, shown as a top banner) or
 * a `graphic` (an inline SVG line-motif on a tinted panel), then eyebrow / title
 * / body / optional footer. Plain content cards keep `MarketingCard`.
 *
 * `tone` (1–3) opts the card into the palette wash rotation (DESIGN.md §2.6):
 * a tinted card background + the matching accent eyebrow color. Sibling cards
 * in a grid take 1, 2, 3 in order — the rotation encodes sibling identity.
 */
const TONES = {
  1: { card: "bg-wash1", eyebrow: "text-acc1-fg" },
  2: { card: "bg-wash2", eyebrow: "text-acc2-fg" },
  3: { card: "bg-wash3", eyebrow: "text-acc4-fg" },
} as const;

export function FeatureCard({
  image,
  graphic,
  eyebrow,
  title,
  body,
  footer,
  tone,
  className,
}: {
  image?: { src: string; alt: string };
  graphic?: ReactNode;
  eyebrow?: string;
  title: string;
  body: string;
  footer?: ReactNode;
  tone?: 1 | 2 | 3;
  className?: string;
}) {
  // eslint-disable-next-line security/detect-object-injection -- tone is typed 1|2|3 against a module-level const map
  const toneClasses = tone ? TONES[tone] : undefined;
  return (
    <MarketingCard
      className={cn(
        "flex h-full flex-col overflow-hidden p-0",
        toneClasses?.card,
        className,
      )}
    >
      {image ? (
        <div className="relative aspect-[16/11] w-full">
          <Image
            src={image.src}
            alt={image.alt}
            fill
            sizes="(max-width: 860px) 100vw, 33vw"
            className="object-cover"
          />
        </div>
      ) : (
        <div className="relative flex h-28 items-center justify-center overflow-hidden bg-surface-panel-tint">
          <Halftone className="absolute inset-0 opacity-[0.12] [mask-image:radial-gradient(circle_at_60%_50%,#000,transparent_72%)]" />
          <div className="relative">{graphic}</div>
        </div>
      )}
      <div className="flex flex-1 flex-col p-7">
        {eyebrow ? (
          <span
            className={cn(
              "font-mono text-sm",
              toneClasses?.eyebrow ?? "text-primary",
            )}
          >
            {eyebrow}
          </span>
        ) : null}
        <h3 className="mt-2 font-serif text-xl font-medium leading-[1.2] text-foreground">
          {title}
        </h3>
        <p className="mt-2 text-[15px] leading-[1.55] text-muted-foreground">
          {body}
        </p>
        {footer ? <div className="mt-auto pt-4">{footer}</div> : null}
      </div>
    </MarketingCard>
  );
}
