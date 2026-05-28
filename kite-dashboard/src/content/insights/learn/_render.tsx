import Link from "next/link";

/**
 * Minimal inline-markup renderer for learn-explainer bodies.
 *
 * Supports: **bold**, _italic_, [text](url), `code`. Block-level: blank-
 * line paragraph breaks; lines starting with "- " or "• " become list
 * items (consecutive items grouped into one <ul>).
 *
 * Anything more elaborate (tables, headings inside a section) should
 * either be expressed as a separate section in the LearnExplainer or
 * upgraded to a real markdown library later. Kept tiny on purpose.
 */

type Token =
  | { kind: "text"; value: string }
  | { kind: "bold"; value: string }
  | { kind: "italic"; value: string }
  | { kind: "code"; value: string }
  | { kind: "link"; text: string; href: string };

const TOKEN_RE =
  /(\*\*[^*]+\*\*)|(_[^_]+_)|(`[^`]+`)|(\[[^\]]+\]\([^)]+\))/g;

function tokenize(line: string): Token[] {
  const out: Token[] = [];
  let lastIndex = 0;
  for (const m of line.matchAll(TOKEN_RE)) {
    if (m.index! > lastIndex) {
      out.push({ kind: "text", value: line.slice(lastIndex, m.index) });
    }
    const tok = m[0];
    if (tok.startsWith("**")) {
      out.push({ kind: "bold", value: tok.slice(2, -2) });
    } else if (tok.startsWith("_")) {
      out.push({ kind: "italic", value: tok.slice(1, -1) });
    } else if (tok.startsWith("`")) {
      out.push({ kind: "code", value: tok.slice(1, -1) });
    } else {
      const linkMatch = /\[([^\]]+)\]\(([^)]+)\)/.exec(tok);
      if (linkMatch) {
        out.push({ kind: "link", text: linkMatch[1], href: linkMatch[2] });
      }
    }
    lastIndex = m.index! + tok.length;
  }
  if (lastIndex < line.length) {
    out.push({ kind: "text", value: line.slice(lastIndex) });
  }
  return out;
}

function renderTokens(tokens: Token[]): React.ReactNode {
  return tokens.map((t, i) => {
    switch (t.kind) {
      case "text":
        return <span key={i}>{t.value}</span>;
      case "bold":
        return <strong key={i}>{t.value}</strong>;
      case "italic":
        return <em key={i}>{t.value}</em>;
      case "code":
        return (
          <code
            key={i}
            className="rounded bg-neutral-100 px-1 py-0.5 text-[0.85em] dark:bg-neutral-800"
          >
            {t.value}
          </code>
        );
      case "link":
        if (t.href.startsWith("/")) {
          return (
            <Link key={i} href={t.href} className="underline underline-offset-2">
              {t.text}
            </Link>
          );
        }
        return (
          <a
            key={i}
            href={t.href}
            target="_blank"
            rel="noopener noreferrer"
            className="underline underline-offset-2"
          >
            {t.text}
          </a>
        );
    }
  });
}

export function RenderBody({ body }: { body: string }) {
  const paragraphs = body.trim().split(/\n{2,}/);
  return (
    <div className="space-y-3 leading-relaxed text-neutral-800 dark:text-neutral-200">
      {paragraphs.map((para, pi) => {
        const lines = para.split("\n");
        const isListBlock = lines.every(
          (l) => l.startsWith("- ") || l.startsWith("• "),
        );
        if (isListBlock) {
          return (
            <ul key={pi} className="ml-5 list-disc space-y-1">
              {lines.map((l, li) => (
                <li key={li}>{renderTokens(tokenize(l.slice(2)))}</li>
              ))}
            </ul>
          );
        }
        return <p key={pi}>{renderTokens(tokenize(para))}</p>;
      })}
    </div>
  );
}
