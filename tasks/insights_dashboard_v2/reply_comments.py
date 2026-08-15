"""Reply to and resolve Vercel Toolbar comment threads.

The other half of the copy-review loop: `read_comments.py` pulls the
founder's notes off the page, this posts back what was done and marks
each thread resolved, so the toolbar itself shows what is still
outstanding instead of that living in someone's head.

Both endpoints are undocumented in the public REST reference and were
found by probing:
    POST  /v1/toolbar/threads/{id}/messages   {"markdown": "..."}
    PATCH /v1/toolbar/threads/{id}            {"resolved": true}

Usage — a JSON object of {thread_id: reply text} on stdin:
    echo '{"abc123": "Applied — heading now reads X."}' \
        | python tasks/insights_dashboard_v2/reply_comments.py
    ... | python tasks/insights_dashboard_v2/reply_comments.py --no-resolve
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
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


def _team() -> str:
    with open(PROJECT_JSON) as fh:
        return json.load(fh)["orgId"]


def _call(method: str, path: str, token: str, body: dict | None = None) -> tuple[int, str]:
    data = json.dumps(body).encode() if body is not None else None
    # S310: scheme and host are fixed by API above; `path` is route + query.
    req = urllib.request.Request(  # noqa: S310
        API + path,
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:  # noqa: S310
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-resolve", action="store_true",
                    help="Post the reply but leave the thread open")
    args = ap.parse_args()

    try:
        replies: dict[str, str] = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        sys.exit(f"stdin must be a JSON object of {{thread_id: reply}} — {exc}")

    token, team = _token(), _team()
    failures = 0
    for thread_id, message in replies.items():
        status, payload = _call(
            "POST", f"/v1/toolbar/threads/{thread_id}/messages?teamId={team}",
            token, {"markdown": message},
        )
        if status != 200:
            print(f"✗ {thread_id} reply failed [{status}] {payload[:120]}")
            failures += 1
            continue
        if args.no_resolve:
            print(f"✓ {thread_id} replied")
            continue
        status, payload = _call(
            "PATCH", f"/v1/toolbar/threads/{thread_id}?teamId={team}",
            token, {"resolved": True},
        )
        if status != 200:
            print(f"~ {thread_id} replied, resolve failed [{status}] {payload[:120]}")
            failures += 1
        else:
            print(f"✓ {thread_id} replied + resolved")

    if failures:
        sys.exit(f"{failures} thread(s) had problems")


if __name__ == "__main__":
    main()
