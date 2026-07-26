import Image from "next/image";

/**
 * Editorial reading-page primitives for /library, matched to the
 * @marketworks/design brand guide's "Library / Reading Page" board:
 * 680px reading column, eyebrow → Fraunces title → byline, Outfit lead +
 * body, signal-green pull-quote, white figure card, lichen-tint takeaway.
 *
 * All consume the brand role tokens provided by the `.mw-brand` scope in
 * the /library layout (font-serif = Fraunces, inherited sans = Outfit).
 */

export function Article({ children }: { children: React.ReactNode }) {
  return (
    <article className="mx-auto flex w-full max-w-[680px] flex-col gap-7 px-6 py-16 sm:py-20">
      {children}
    </article>
  );
}

export function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-[13px] font-semibold uppercase tracking-[0.15em] text-primary">
      {children}
    </span>
  );
}

export function PieceHeader({
  eyebrow,
  title,
  byline,
}: {
  eyebrow: string;
  title: string;
  byline: string;
}) {
  return (
    <header className="flex flex-col gap-4">
      <Eyebrow>{eyebrow}</Eyebrow>
      <h1 className="font-serif text-[2.5rem] font-medium leading-[1.08] tracking-[-0.02em] text-foreground sm:text-[3.25rem]">
        {title}
      </h1>
      <p className="text-[15px] text-muted-foreground">{byline}</p>
    </header>
  );
}

/** The hook — rendered as the lead paragraph (20px). */
export function Lead({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-xl leading-[1.6] text-foreground">{children}</p>
  );
}

export function BodyParagraph({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[17px] leading-[1.62] text-[color:var(--brand-prose)]">
      {children}
    </p>
  );
}

export function PullQuote({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <figure className="flex flex-col gap-[18px] py-3">
      <div className="h-[3px] w-14 rounded-full bg-secondary" />
      <blockquote className="font-serif text-[28px] font-medium italic leading-[1.25] tracking-[-0.01em] text-primary sm:text-[32px]">
        {children}
      </blockquote>
    </figure>
  );
}

/** White card wrapping a rendered social asset (thumbnail / carousel). */
export function Figure({
  src,
  alt,
  caption,
  width = 1080,
  height = 1080,
  priority,
}: {
  src: string;
  alt: string;
  caption?: string;
  width?: number;
  height?: number;
  priority?: boolean;
}) {
  return (
    <figure className="flex flex-col gap-4 rounded-xl border border-border bg-card p-4">
      <Image
        src={src}
        alt={alt}
        width={width}
        height={height}
        priority={priority}
        className="w-full rounded-lg"
      />
      {caption && (
        <figcaption className="text-[13px] leading-[1.4] text-muted-foreground">
          {caption}
        </figcaption>
      )}
    </figure>
  );
}

export function TakeawayCard({ children }: { children: React.ReactNode }) {
  return (
    <aside className="flex flex-col gap-2.5 rounded-xl bg-wash2 p-7">
      <span className="text-xs font-semibold uppercase tracking-[0.16em] text-acc2-fg">
        The takeaway
      </span>
      <p className="font-serif text-2xl font-medium leading-[1.3] text-foreground">
        {children}
      </p>
    </aside>
  );
}

export function CtaCard({ children }: { children: React.ReactNode }) {
  return (
    <aside className="flex items-start gap-3 rounded-xl border border-border bg-card p-6">
      <span aria-hidden className="mt-0.5 text-primary">
        →
      </span>
      <p className="text-[17px] leading-[1.5] text-foreground">{children}</p>
    </aside>
  );
}

export function SourceData({
  dataPoints,
  sourceSignal,
}: {
  dataPoints: string[];
  sourceSignal?: string;
}) {
  return (
    <details className="rounded-xl border border-border bg-card p-6 text-sm">
      <summary className="cursor-pointer font-medium text-foreground">
        Source data
      </summary>
      <p className="mt-3 text-[13px] text-muted-foreground">
        Grounded in Marketworks&apos; insight engine — the following live
        readings:
      </p>
      <ul className="mt-3 list-disc space-y-1 pl-5 text-[color:var(--brand-prose)]">
        {dataPoints.map((dp, i) => (
          <li key={i}>{dp}</li>
        ))}
      </ul>
      {sourceSignal && (
        <p className="mt-3 text-[13px] text-muted-foreground">
          Source: {sourceSignal}
        </p>
      )}
    </details>
  );
}
