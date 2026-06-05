import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getAllSlugs, getPiece } from "@/lib/library";
import { byline, humanizeFormat } from "@/lib/library-format";
import {
  Article,
  PieceHeader,
  Lead,
  BodyParagraph,
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
        byline={byline(piece.format, piece.published_at)}
      />

      {thumbnail && (
        <Figure src={thumbnail.path} alt={thumbnail.alt} priority />
      )}

      {piece.hook && <Lead>{piece.hook}</Lead>}

      {piece.body.map((section, i) => (
        <BodyParagraph key={i}>{section}</BodyParagraph>
      ))}

      {piece.key_takeaway && <TakeawayCard>{piece.key_takeaway}</TakeawayCard>}

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
