import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getAllSlugs, getPiece } from "@/lib/library";
import { byline, humanizeFormat } from "@/lib/library-format";
import { Fragment } from "react";

import {
  Article,
  PieceHeader,
  Lead,
  BodyParagraph,
  SectionHeading,
  PullQuote,
  Figure,
  TakeawayCard,
  CtaCard,
  SourceData,
} from "@/components/library/article";

export function generateStaticParams() {
  return getAllSlugs().map((slug) => ({ slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const piece = getPiece(slug);
  if (!piece) {
    return { title: "Not found — Marketworks" };
  }
  const thumb = piece.assets.find((a) => a.type === "thumbnail");
  return {
    title: `${piece.title} — Marketworks`,
    description: piece.hook || piece.key_takeaway,
    openGraph: {
      title: piece.title,
      description: piece.hook || piece.key_takeaway,
      images: thumb ? [{ url: thumb.path }] : undefined,
    },
  };
}

export default async function LibraryPiece({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const piece = getPiece(slug);
  if (!piece) {
    notFound();
  }

  const thumbnail = piece.assets.find((a) => a.type === "thumbnail");

  // Article-shaped pieces (published from a derived article.json) carry
  // sections with headings; their key_takeaway is the article's pull-quote,
  // rendered mid-read rather than as a closing takeaway card. Script-shaped
  // pieces keep the flat-paragraph body + takeaway card.
  const sections = piece.sections ?? [];
  const hasSections = sections.length > 0;
  const pullQuoteAfter = Math.ceil(sections.length / 2) - 1;

  return (
    <Article>
      <Link
        href="/library"
        className="text-[13px] font-medium text-muted-foreground transition-colors hover:text-foreground"
      >
        ← Library
      </Link>

      <PieceHeader
        eyebrow={`${piece.pillar} · ${humanizeFormat(piece.format)}`}
        title={piece.title}
        byline={byline(piece.format, piece.published_at, piece.duration)}
      />

      {thumbnail && (
        <Figure src={thumbnail.path} alt={thumbnail.alt} priority />
      )}

      {piece.hook && <Lead>{piece.hook}</Lead>}

      {hasSections
        ? sections.map((section, i) => (
            <Fragment key={i}>
              {section.heading && (
                <SectionHeading>{section.heading}</SectionHeading>
              )}
              <BodyParagraph>{section.text}</BodyParagraph>
              {i === pullQuoteAfter && piece.key_takeaway && (
                <PullQuote>{piece.key_takeaway}</PullQuote>
              )}
            </Fragment>
          ))
        : piece.body.map((section, i) => (
            <BodyParagraph key={i}>{section}</BodyParagraph>
          ))}

      {!hasSections && piece.key_takeaway && (
        <TakeawayCard>{piece.key_takeaway}</TakeawayCard>
      )}

      {piece.cta && <CtaCard>{piece.cta}</CtaCard>}

      {piece.meta.data_points && piece.meta.data_points.length > 0 && (
        <SourceData
          dataPoints={piece.meta.data_points}
          sourceSignal={piece.meta.source_signal}
        />
      )}
    </Article>
  );
}
