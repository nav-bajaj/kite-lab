"""Read Vercel Toolbar comment threads for the copy-review loop.

The founder marks up copy directly on localhost:3000 using the Vercel
Toolbar (mounted in dev only — see kite-dashboard/src/app/layout.tsx);
this prints those threads so the agent can act on them without anything
being retyped into chat.

Auth: the Vercel CLI's own token (`vercel login` writes it). The
claude.ai Vercel MCP connector cannot read these — it returns no teams
for this account — so the REST API with the CLI token is the path that
works. `GET /v1/toolbar/threads` is undocumented in the public REST
reference; it was found by probing and may change without notice.

Usage:
    python tasks/insights_dashboard_v2/read_comments.py
    python tasks/insights_dashboard_v2/read_comments.py --status resolved
    python tasks/insights_dashboard_v2/read_comments.py --page '/insights*'
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

AUTH_PATH = os.path.expanduser(
    "~/Library/Application Support/com.vercel.cli/auth.json"
)
PROJECT_JSON = os.path.join(
    os.path.dirname(__file__), "..", "..", "kite-dashboard", ".vercel", "project.json"
)
API = "https://api.vercel.com"


def _token() -> str:
    try:
        with open(AUTH_PATH) as fh:
            return json.load(fh)["token"]
    except (OSError, KeyError) as exc:
        sys.exit(f"No Vercel CLI token at {AUTH_PATH} — run `vercel login`. ({exc})")


def _team_and_project() -> tuple[str, str]:
    with open(PROJECT_JSON) as fh:
        cfg = json.load(fh)
    return cfg["orgId"], cfg["projectId"]


def _get(path: str, token: str) -> dict:
    # S310: the scheme is fixed by the API constant above — `path` only ever
    # contributes the route and query string, never the scheme or host.
    req = urllib.request.Request(  # noqa: S310
        API + path, headers={"Authorization": f"Bearer {token}"}
    )
    try:
        with urllib.request.urlopen(req) as resp:  # noqa: S310
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        sys.exit(f"{exc.code} from {path}: {exc.read()[:300].decode('utf-8', 'replace')}")


def _text_of(message: dict) -> str:
    """Messages carry markdown; fall back to any plain-text field."""
    for key in ("markdown", "text", "body", "content"):
        value = message.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return json.dumps(message)[:200]


def _selected_element(framework_context: str | None) -> str | None:
    """Pull the `Selected: <...>` line out of the React tree the toolbar
    captures — a hint at which component to edit, not a source location."""
    if not framework_context:
        return None
    for line in framework_context.splitlines():
        if line.startswith("Selected:"):
            return line[len("Selected:"):].strip()
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--status", default="unresolved", choices=["unresolved", "resolved"])
    ap.add_argument("--page", help="Filter by page path or glob, e.g. '/insights*'")
    ap.add_argument("--branch", help="Filter by git branch")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--component", action="store_true",
                    help="Also show the selected React element")
    ap.add_argument("--raw", action="store_true", help="Dump the raw JSON payload")
    args = ap.parse_args()

    token = _token()
    team, project = _team_and_project()
    query = {"teamId": team, "projectId": project, "status": args.status,
             "limit": str(args.limit)}
    if args.page:
        query["page"] = args.page
    if args.branch:
        query["branch"] = args.branch

    payload = _get("/v1/toolbar/threads?" + urllib.parse.urlencode(query), token)
    if args.raw:
        print(json.dumps(payload, indent=2))
        return

    threads = payload.get("threads", [])
    if not threads:
        print(f"No {args.status} threads. Leave a comment via the toolbar on "
              f"localhost:3000, then re-run.")
        return

    # Oldest first: the founder comments top-down the page, so this reads in
    # roughly the order the notes were made.
    threads.sort(key=lambda t: ((t.get("messages") or [{}])[0].get("timestamp") or 0))

    print(f"{len(threads)} {args.status} thread(s)\n")
    for thread in threads:
        context = thread.get("context") or {}
        print(f"── {thread.get('id', '?')}  ·  {context.get('path', '?')}")
        # The single most useful field: the exact on-page text the note is
        # pinned to, which is what has to be found in the source.
        selection = context.get("selection")
        if selection:
            print(f'   on: "{selection.strip()[:300]}"')
        if args.component:
            element = _selected_element(context.get("frameworkContext"))
            if element:
                print(f"   element: {element}")
        for message in thread.get("messages", []) or []:
            author = (message.get("author") or {}).get("username") or "?"
            print(f"   → [{author}] {_text_of(message)}")
        print()


if __name__ == "__main__":
    main()
