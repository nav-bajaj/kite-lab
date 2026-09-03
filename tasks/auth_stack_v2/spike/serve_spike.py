"""
S0.6 throwaway spike server — NOT production code.

Serves a minimal sign-in page on http://localhost:3000 (port matters:
it must match the Supabase project's redirect-URL allowlist), templated
with the scratch project's URL + anon key fetched from the Supabase CLI
at startup so no key lands in the repo. When the page obtains a
session it POSTs the access token to /capture, which writes
`.captured_token` (gitignored) for verify_spike_token.py.

Run: python tasks/auth_stack_v2/spike/serve_spike.py
"""

import json
import pathlib
import shutil
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PROJECT_REF = "jhvkfokskanbaiipvcqu"
PROJECT_URL = f"https://{PROJECT_REF}.supabase.co"
PORT = 3000
HERE = pathlib.Path(__file__).parent
TOKEN_FILE = HERE / ".captured_token"


def anon_key() -> str:
    cli = shutil.which("supabase")
    if cli is None:
        sys.exit("supabase CLI not found on PATH")
    out = subprocess.run(
        [cli, "projects", "api-keys", "--project-ref", PROJECT_REF,
         "-o", "json"],
        capture_output=True, text=True, check=True,
    ).stdout
    return [k["api_key"] for k in json.loads(out) if k["name"] == "anon"][0]


PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>auth_stack_v2 spike</title></head>
<body style="font-family: monospace; max-width: 640px; margin: 3rem auto;">
<h2>auth_stack_v2 — S0.6 spike sign-in</h2>
<p>Scratch project: __PROJECT_URL__</p>
<button id="google" style="padding:0.6rem 1.2rem;">Sign in with Google</button>
<pre id="out" style="white-space:pre-wrap;background:#f4f4f4;padding:1rem;"></pre>
<script type="module">
import { createClient } from "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm";
const sb = createClient("__PROJECT_URL__", "__ANON_KEY__");
const out = document.getElementById("out");
document.getElementById("google").onclick = () =>
  sb.auth.signInWithOAuth({ provider: "google",
    options: { redirectTo: "http://localhost:3000" } });
// refreshSession so server-side app_metadata changes (e.g. the admin
// role set via the admin API) appear in the captured token instead of
// the cached one from the original sign-in.
let { data: { session } } = await sb.auth.getSession();
if (session) {
  const refreshed = await sb.auth.refreshSession();
  if (refreshed.data.session) session = refreshed.data.session;
}
if (session) {
  out.textContent = "session captured — posting to /capture ...";
  await fetch("/capture", { method: "POST", body: session.access_token });
  out.textContent =
    "access token captured to .captured_token\\n\\nsub: " + session.user.id +
    "\\nemail: " + session.user.email +
    "\\napp_metadata: " + JSON.stringify(session.user.app_metadata) +
    "\\n\\nYou can close this tab and return to the terminal.";
} else {
  out.textContent = "no session yet — click the button.";
}
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    page = b""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(self.page)

    def do_POST(self):
        if self.path == "/capture":
            length = int(self.headers.get("Content-Length", 0))
            token = self.rfile.read(length).decode()
            TOKEN_FILE.write_text(token)
            TOKEN_FILE.chmod(0o600)
            print(f"[spike] token captured -> {TOKEN_FILE}", flush=True)
            self.send_response(204)
            self.end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    key = anon_key()
    Handler.page = (
        PAGE.replace("__PROJECT_URL__", PROJECT_URL)
        .replace("__ANON_KEY__", key)
        .encode()
    )
    print(f"[spike] serving http://localhost:{PORT} — sign in with Google",
          flush=True)
    try:
        HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    except OSError as exc:
        sys.exit(f"port {PORT} busy ({exc}) — stop the dev server first")
