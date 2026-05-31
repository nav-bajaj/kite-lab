import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getAllSlugs, getPiece } from "@/lib/library";

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

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  } catch {
    return iso;
  }
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
  const carousel = piece.assets.filter((a) => a.type === "carousel");

  return (
    <article className="mx-auto max-w-3xl px-6 py-12">
      <nav className="mb-8 text-xs uppercase tracking-wider text-neutral-500">
        <Link href="/library" className="hover:underline">
          Library
        </Link>
        <span className="mx-2">/</span>
        <span>{piece.pillar}</span>
      </nav>

      <header className="mb-10">
        <h1 className="text-4xl font-semibold tracking-tight">{piece.title}</h1>
        <div className="mt-4 flex items-center gap-4 text-xs uppercase tracking-wider text-neutral-500">
          <time>{formatDate(piece.published_at)}</time>
          <span>·</span>
          <span>{piece.format}</span>
          {piece.duration && (
            <>
              <span>·</span>
              <span>{piece.duration}</span>
            </>
          )}
        </div>
      </header>

      {thumbnail && (
        <div className="mb-10 overflow-hidden rounded-lg border border-neutral-200 dark:border-neutral-800">
          <Image
            src={thumbnail.path}
            alt={thumbnail.alt}
            width={1280}
            height={720}
            className="w-full"
            priority
          />
        </div>
      )}

      {piece.hook && (
        <p className="mb-10 text-xl font-medium leading-relaxed text-neutral-900 dark:text-neutral-100">
          {piece.hook}
        </p>
      )}

      <div className="prose prose-neutral max-w-none dark:prose-invert">
        {piece.body.map((section, i) => (
          <p key={i}>{section}</p>
        ))}
      </div>

      {piece.key_takeaway && (
        <div className="my-10 rounded-md border-l-4 border-emerald-500 bg-emerald-50/50 p-6 dark:bg-emerald-950/20">
          <p className="text-xs uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
            Takeaway
          </p>
          <p className="mt-2 text-base text-neutral-800 dark:text-neutral-200">
            {piece.key_takeaway}
          </p>
        </div>
      )}

      {carousel.length > 0 && (
        <section className="my-12">
          <h2 className="mb-4 text-sm font-medium uppercase tracking-wider text-neutral-500">
            Carousel
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {carousel.map((asset) => (
              <Image
                key={asset.filename}
                src={asset.path}
                alt={asset.alt}
                width={1080}
                height={1080}
                className="rounded-md border border-neutral-200 dark:border-neutral-800"
              />
            ))}
          </div>
        </section>
      )}

      {piece.cta && (
        <div className="my-10 rounded-md border border-neutral-200 p-6 dark:border-neutral-800">
          <p className="text-base text-neutral-800 dark:text-neutral-200">
            {piece.cta}
          </p>
        </div>
      )}

      {piece.meta.data_points && piece.meta.data_points.length > 0 && (
        <details className="my-10 rounded-md border border-neutral-200 p-6 text-sm dark:border-neutral-800">
          <summary className="cursor-pointer font-medium">
            Source data
          </summary>
          <p className="mt-3 text-xs text-neutral-600 dark:text-neutral-400">
            This piece was sourced from Marketworks&apos; insight engine
            and grounded in the following live readings:
          </p>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-neutral-700 dark:text-neutral-300">
            {piece.meta.data_points.map((dp, i) => (
              <li key={i}>{dp}</li>
            ))}
          </ul>
          {piece.meta.source_signal && (
            <p className="mt-3 text-xs text-neutral-500">
              Source: {piece.meta.source_signal}
            </p>
          )}
        </details>
      )}

      <footer className="mt-16 border-t border-neutral-200 pt-6 text-xs text-neutral-500 dark:border-neutral-800">
        Educational content from Marketworks. Not investment advice. See{" "}
        <Link href="/disclaimer" className="underline">
          disclaimer
        </Link>
        .
      </footer>
    </article>
  );
}
