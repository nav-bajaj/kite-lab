/**
 * Render every React Email template to static HTML + plaintext for the
 * Python sender (tasks/email_channel PLAN §3).
 *
 * The architecture: React owns how emails LOOK, Python owns the data and
 * the SES send. This script is the seam. Output lands in
 * kite-api/app/emails/ and is committed, so production needs no Node
 * runtime and no build step at deploy time.
 *
 * Placeholders like {{unsubscribe_url}} survive into the output because
 * the templates default those props to the literal token. Python does a
 * closed-set, HTML-escaped substitution — never a general templating
 * language. The moment a template needs a loop or a conditional, that is
 * the signal to move to a Node render service, not to grow a dialect here.
 *
 *   npm run emails:export
 */
import { readdir, mkdir, writeFile } from "node:fs/promises";
import { join, dirname, basename } from "node:path";
import { fileURLToPath } from "node:url";

import React from "react";
import { render, pretty } from "react-email";

const here = dirname(fileURLToPath(import.meta.url));
const EMAIL_DIR = join(here, "..", "emails");
const OUT_DIR = join(here, "..", "..", "kite-api", "app", "emails");

const entries = (await readdir(EMAIL_DIR, { withFileTypes: true }))
  .filter((e) => e.isFile() && /\.(tsx|jsx)$/.test(e.name))
  .filter((e) => !e.name.startsWith("_"));

if (entries.length === 0) {
  console.error("No templates found in emails/");
  process.exit(1);
}

await mkdir(OUT_DIR, { recursive: true });

for (const entry of entries) {
  const name = basename(entry.name).replace(/\.(tsx|jsx)$/, "");
  // Names come from readdir of a fixed directory, but constrain them
  // anyway: these feed a path we write to, and a template called
  // `../../x` should fail loudly rather than escape OUT_DIR.
  if (!/^[a-z0-9][a-z0-9_-]*$/i.test(name)) {
    console.error(`${entry.name}: unsafe template name, skipping`);
    continue;
  }
  const mod = await import(join(EMAIL_DIR, entry.name));
  const Template = mod.default;
  if (typeof Template !== "function") {
    console.error(`${entry.name}: no default export, skipping`);
    continue;
  }

  const el = React.createElement(Template);
  const html = await pretty(await render(el));
  // render(plainText:true) once — NOT toPlainText() over an already-plain
  // string, which collapses every paragraph onto a single line.
  const text = await render(el, { plainText: true });

  // Build-time script; `name` is validated above against a strict allowlist
  // and OUT_DIR is a constant, so no caller-controlled path reaches here.
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- validated name, constant dir
  await writeFile(join(OUT_DIR, `${name}.html`), html, "utf8");
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- validated name, constant dir
  await writeFile(join(OUT_DIR, `${name}.txt`), text, "utf8");

  // Surface the placeholders so a template that silently loses its
  // unsubscribe token cannot pass unnoticed — that link is a legal
  // requirement, not a nicety.
  const tokens = [...html.matchAll(/\{\{(\w+)\}\}/g)].map((m) => m[1]);
  console.log(
    `${name}: ${html.length} bytes html, ${text.length} bytes text, ` +
      `tokens=[${[...new Set(tokens)].join(", ") || "none"}]`
  );
}
